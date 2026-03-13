# Pretrain models[](#pretrain-models)

Pretraining large-scale models requires high performance, flexibility, and scalability. Lightning AI offers tools and strategies to accelerate model pretraining on multi-GPU and multi-node systems, with deep support for PyTorch Lightning and Lightning Fabric.

## Multi-GPU training[](#multi-gpu-training)

Leverage multiple GPUs to reduce training time and increase throughput for large models and datasets.

* *Key features: **

  - Scale training across multiple GPUs on a single machine

  - Automatic device management and parallelization

  - Support for mixed precision to reduce memory usage


## Multi-node training[](#multi-node-training)

Distribute training across multiple machines to handle massive models or datasets.

* *Key features: **

  - Scale training jobs across clusters

  - Efficient communication between nodes

  - Easy integration with SLURM and other job schedulers


## PyTorch Lightning[](#pytorch-lightning)

PyTorch Lightning provides a high-level interface for organizing PyTorch code and scaling training with minimal boilerplate.

* *Key features: **

  - Clean, structured code for training and validation loops

  - Built-in support for logging, checkpointing, and distributed training

  - Compatible with native PyTorch models


## Lightning Fabric[](#lightning-fabric)

Lightning Fabric is a flexible, lower-level framework designed for full control over training and scaling logic.

* *Key features: **

  - Fine-grained control over training steps and optimization

  - Lightweight primitives for multi-GPU and multi-node training

  - Ideal for custom research and large-scale model development


## Continual pretraining[](#continual-pretraining)

Continue training pre-existing models on new data while retaining previously learned knowledge.

* *Key features: **

  - Incrementally update models without retraining from scratch

  - Maintain performance across evolving datasets

  - Ideal for domain adaptation and long-term model improvement


