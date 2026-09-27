#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import torch
import torch.nn as nn
from pathlib import Path

# Add current directory to path to import transnetv2_pytorch
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

def main():
    base_dir = Path(__file__).parent.parent.parent
    weights_path = base_dir / "assets" / "transnetv2-pytorch-weights.pth"
    onnx_dir = base_dir / "assets" / "models" / "onnx"
    onnx_dir.mkdir(parents=True, exist_ok=True)
    onnx_path = onnx_dir / "transnetv2.onnx"

    if not weights_path.exists():
        print(f"Error: Weights not found at {weights_path}")
        sys.exit(1)

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
    print("Export completed successfully!")

if __name__ == "__main__":
    main()
