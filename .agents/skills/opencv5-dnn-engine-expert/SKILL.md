---
name: opencv5-dnn-engine-expert
description: Dédié aux spécificités techniques du moteur d'inférence orienté graphe d'OpenCV 5.0. Gère l'activation du graphe, le target CPU exclusif, et la cascade de fallback (ONNX/TFLite).
---

# OpenCV 5.0 DNN Engine Expert

**TL;DR**: OpenCV 5.0 introduces an experimental graph-oriented inference engine. To use it properly, you must explicitly enable it via `ENGINE_NEW`, enforce `DNN_TARGET_CPU`, and ensure `LD_LIBRARY_PATH` is injected dynamically for correct fallback chains.

## Activation and Environment Management

When working with OpenCV 5.0 in this project, you're interacting with an experimental engine that leverages KleidiCV and Universal Intrinsics (HAL). It requires specific configurations to avoid defaulting to the legacy path.

### ❌ The Legacy Initialization

```python
net = cv2.dnn.readNet(model_path)
net.setPreferableBackend(cv2.dnn.DNN_BACKEND_OPENCV)
```

### ✅ The Graph Engine Initialization

```python
net = cv2.dnn.readNet(model_path)
net.setPreferableBackend(cv2.dnn.DNN_BACKEND_OPENCV)
net.setPreferableTarget(cv2.dnn.DNN_TARGET_CPU)
# Critical: Explicitly request the new graph engine
net.set(cv2.dnn.DNN_ENGINE_NEW, True) 
```

## Dynamic `LD_LIBRARY_PATH` for Fallbacks

OpenCV 5.0 in our stack lives alongside ONNX Runtime and TFLite. If an operator isn't supported (or if the graph fails to compile), we rely on robust fallbacks. 
Virtual environments isolate dependencies, but they often mask system-level CUDA/cuDNN libraries. You must handle `LD_LIBRARY_PATH` dynamically before initializing the engine to ensure ONNX Runtime (CUDA) can boot properly as a fallback.

## Operator Validation Pattern

OpenCV 5.0's DNN module evaluates the graph before execution. We enforce a dry-run pattern for models like TransNetV2 to validate operators (like `Slice`) before real inference begins.

```python
# Dry run to validate the graph and operators
try:
    dummy_input = np.zeros((1, 50, 27, 48, 3), dtype=np.float32)
    net.setInput(dummy_input)
    net.forward()
except cv2.error as e:
    # Route to ONNX Runtime fallback
    logger.warning(f"OpenCV 5.0 DNN failed operator validation: {e}")
```

## The Golden Rule: Test the Graph, Prepare the Fallback

Never assume OpenCV 5.0 will swallow every TFLite or ONNX model flawlessly. Always wrap initialization in a fallback chain targeting ONNX Runtime (CPU/CUDA) or TFLite Interpreter.
