#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
from pathlib import Path

import argparse
import onnx
from onnx import helper, numpy_helper
import numpy as np


def sanitize_transnetv2_for_opencv5(input_onnx_path: str, output_onnx_path: str = None) -> None:
    """
    Réécrit chirurgicalement le graphe transnetv2.onnx pour éliminer les rejets
    de l'importeur OpenCV DNN (Flatten axis=3 / 5D et Mul/Div 0D broadcasting).
    """
    if output_onnx_path is None:
        output_onnx_path = input_onnx_path

    model = onnx.load(input_onnx_path)
    model = onnx.shape_inference.infer_shapes(model)
    graph = model.graph

    value_shapes = {}
    for vi in list(graph.input) + list(graph.value_info) + list(graph.output):
        if vi.type.tensor_type.HasField("shape"):
            dims = [
                d.dim_value if d.dim_value > 0 else -1
                for d in vi.type.tensor_type.shape.dim
            ]
            value_shapes[vi.name] = dims

    initializers = {init.name: init for init in graph.initializer}
    new_nodes = []

    for idx, node in enumerate(graph.node):
        # 1. Remplacement chirurgical de Flatten (axis=3 ou 5D) par Reshape explicite
        if node.op_type == "Flatten":
            axis = 1
            for attr in node.attribute:
                if attr.name == "axis":
                    axis = attr.i

            in_name = node.input[0]
            out_name = node.output[0]
            in_shape = value_shapes.get(in_name, [])

            if len(in_shape) > 0 and axis < len(in_shape):
                trailing_dim = int(np.prod(in_shape[axis:]))
            else:
                trailing_dim = 1
            target_shape = np.array([-1, trailing_dim], dtype=np.int64)

            shape_const_name = f"{node.name}_reshape_target_{idx}"
            shape_init = numpy_helper.from_array(target_shape, name=shape_const_name)
            graph.initializer.append(shape_init)

            reshape_node = helper.make_node(
                "Reshape",
                inputs=[in_name, shape_const_name],
                outputs=[out_name],
                name=f"{node.name}_ReplacedFlatten_{idx}",
            )
            new_nodes.append(reshape_node)
            continue

        # 2. Promotion des constantes 0D (scalaires) dans les noeuds Mul / Div en tenseurs 1D
        if node.op_type in ("Mul", "Div"):
            for inp_name in node.input:
                if inp_name in initializers:
                    init_tensor = initializers[inp_name]
                    arr = numpy_helper.to_array(init_tensor)
                    if arr.ndim == 0:
                        other_inps = [i for i in node.input if i != inp_name]
                        if any(len(value_shapes.get(i, [])) >= 2 for i in other_inps):
                            promoted_arr = arr.reshape((1,))
                            new_init = numpy_helper.from_array(promoted_arr, name=inp_name)
                            graph.initializer.remove(init_tensor)
                            graph.initializer.append(new_init)
                            initializers[inp_name] = new_init

        new_nodes.append(node)

    del graph.node[:]
    graph.node.extend(new_nodes)

    onnx.checker.check_model(model)
    onnx.save(model, output_onnx_path)
    print(f"[Sanitization] Modèle ONNX OpenCV 5.0 compatible sauvegardé : {output_onnx_path}")


def main():
    parser = argparse.ArgumentParser(description="Export et sanitization TransNetV2 ONNX.")
    parser.add_argument("--sanitize-only", action="store_true", help="Applique uniquement la sanitization sur le modèle ONNX existant.")
    parser.add_argument("--onnx-path", type=str, default=None, help="Chemin du modèle ONNX cible.")
    args = parser.parse_args()

    base_dir = Path(__file__).parent.parent.parent
    weights_path = base_dir / "assets" / "transnetv2-pytorch-weights.pth"
    onnx_dir = base_dir / "assets" / "models" / "onnx"
    onnx_dir.mkdir(parents=True, exist_ok=True)
    onnx_path = Path(args.onnx_path) if args.onnx_path else onnx_dir / "transnetv2.onnx"

    if args.sanitize_only:
        if not onnx_path.exists():
            print(f"Error: ONNX model not found at {onnx_path}")
            sys.exit(1)
        print(f"Sanitizing existing ONNX model at {onnx_path}...")
        sanitize_transnetv2_for_opencv5(str(onnx_path))
        print("Sanitization completed successfully!")
        return

    if not weights_path.exists():
        print(f"Error: Weights not found at {weights_path}")
        sys.exit(1)

    import torch
    import torch.nn as nn
    sys.path.append(os.path.dirname(os.path.abspath(__file__)))
    from transnetv2_pytorch import TransNetV2

    class InferenceWrapper(nn.Module):
        def __init__(self, base: nn.Module):
            super().__init__()
            self.base = base

        def forward(self, x: torch.Tensor) -> torch.Tensor:
            out = self.base(x)
            if isinstance(out, (tuple, list)):
                return out[0]
            return out

    print(f"Loading weights from {weights_path}...")
    model = TransNetV2()
    state = torch.load(str(weights_path), map_location='cpu')
    model.load_state_dict(state)
    model.eval()

    wrapper = InferenceWrapper(model).eval()

    # TransNetV2 expects input shape: [B, T, 27, 48, 3] where T=100 in uint8
    dummy_input = torch.zeros((1, 100, 27, 48, 3), dtype=torch.uint8)

    print(f"Exporting model to ONNX at {onnx_path}...")
    torch.onnx.export(
        wrapper,
        dummy_input,
        str(onnx_path),
        export_params=True,
        opset_version=13, # recommended opset version for 3D convs
        do_constant_folding=True,
        input_names=['input_frames'],
        output_names=['transition_probabilities'],
        dynamic_axes={
            'input_frames': {0: 'batch_size'},
            'transition_probabilities': {0: 'batch_size'}
        }
    )
    print("Export completed successfully! Now applying OpenCV 5.0 sanitization...")
    sanitize_transnetv2_for_opencv5(str(onnx_path))
    print("Export and sanitization completed successfully!")

if __name__ == "__main__":
    main()
