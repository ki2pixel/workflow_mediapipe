# Single GPU training[](#single-gpu-training)

GPUs dramatically increase training speed compared to CPUs by parallelizing computations in deep learning models.

To learn more about GPUs, [read this guide.](https://lightning.ai/docs/overview/studios/change-gpus)

## Switch from CPU to GPU[](#switch-from-cpu-to-gpu)

Start by debugging and iterating your model on a CPU. Once it’s working, shift to a GPU to speed up the process without extra costs. In Studios, switching is easy and cost-effective.

https://pl-bolts-doc-images.s3.us-east-2.amazonaws.com/Docs\_Studios\_MP4/Docs\_DevelopmentWorkflow\_Step2Iterate\_TestonCheapGPU.mp4

Easily switch from CPU to GPU.

For seamless transitions across CPUs and GPUs, consider utilizing our [PyTorch Lightning](https://lightning.ai/docs/pytorch/stable/?referrer=platform-docs) library. It supports fine-tuning and pre-training on any hardware with zero code changes.

## Monitor GPU use[](#monitor-gpu-use)

The top of the Studio shows metrics about the GPU. If the GPU RAM isn’t fully used or the utilization isn’t constantly at 100%, adjust your model's hyperparameters to utilize the full GPU capacity.

https://pl-bolts-doc-images.s3.us-east-2.amazonaws.com/Docs\_Studios\_MP4/Docs\_TrainModels\_MonitoringGPUEfficiency.mp4

Easily monitor your GPU utilization, VRAM, temperature and power.

