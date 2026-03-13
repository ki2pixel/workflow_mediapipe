# Multi-GPU training[](#multi-gpu-training)

Multi-GPU training enables massive speed ups to model training. As a general guideline, doubling the GPUs halves the training time. For example, if a model trains in 24 hours on 1 GPU you can expect it to take 12 hours on 2 GPUs or 6 hours on 4 GPUs.

Achieving such linear speed-ups requires a LOT of effort. Tools like PyTorch Lightning and Studios are here to simplify the process by handling distribution efficiently.

https://pl-bolts-doc-images.s3.us-east-2.amazonaws.com/Docs\_Studios\_MP4/TrainModel\_MultiGPUTraining2.mp4

Scale your training to multi-GPU.

# Run on multiple GPUs[](#run-on-multiple-gpus)

If you've never tried using multiple GPUs, then it's likely that you are not using the right tools. Today, we're going to change that. Start a Studio and change to 4 GPUs.

https://pl-bolts-doc-images.s3.us-east-2.amazonaws.com/Docs\_Studios\_MP4/Docs\_TrainModels\_SwitchToMultiGPU.mp4

Easily switch from CPU to multiple GPUs.

## PyTorch Lightning multi-GPU[](#pytorch-lightning-multi-gpu)

For [PyTorch Lightning](https://lightning.ai/docs/pytorch/stable/?referrer=platform-docs) or [Fabric](https://lightning.ai/docs/fabric/stable/?referrer=platform-docs) users, simply rerun your code without the ` accelerator ` or ` num_devices ` arguments. These tools automatically detect the 4 GPUs. There are zero code changes required.

https://pl-bolts-doc-images.s3.us-east-2.amazonaws.com/Docs\_Studios\_MP4/Docs\_TrainModels\_SwitchToMultiGPU2.mp4

Use PyTorch Lightning or Lightning Fabric to switch machines with no code changes\!

## PyTorch multi-GPU[](#pytorch-multi-gpu)

Running on multiple GPUs without [PyTorch Lightning](https://lightning.ai/docs/pytorch/stable/?referrer=platform-docs) takes a significant amount of work. In this setting, all the details matter such as:

  - How to save checkpoints.

  - Early Stopping.

  - Logging.

  - Compute distributed metrics.

  - ...


However, if you are confident you have handled these considerations, the Studio provides useful environment variables for your setup.

  - ` MASTER_ADDR`

  - ` MASTER_PORT`

  - ` RANK`

  - ` LOCAL_RANK`

  - ` WORLD_SIZE`


Here's how you might set up the distributed environment for PyTorch:

`1 2 3 4 5 6 7 8 9 10 ` ` import os device = "cuda" if torch.cuda.is_available() else "cpu" nprocs = torch.cuda.device_count() if device == "cuda" else 1 master_addr = os.environ.get("MASTER_ADDR", "127.0.0.1") master_port = os.environ.get("MASTER_PORT", "6006") global_rank = int(os.environ.get("RANK", -1)) local_rank = int(os.environ.get("LOCAL_RANK", -1)) world_size = int(os.environ.get("WORLD_SIZE", nprocs))`

* *Note ** : Connecting the machines is relatively simple, but successful training still requires all the considerations we mentioned. We recommend you look into Fabric or PyTorch Lightning which handles all other training logistics for you.

## Other frameworks[](#other-frameworks)

To use multiple GPUs with other frameworks, refer to the documentation of the framework which usually requires a few environment variables available on the Studio:

  - ` MASTER_ADDR`

  - ` MASTER_PORT`

  - ` RANK`

  - ` LOCAL_RANK`

  - ` WORLD_SIZE`


Here's an example on how to access these in Python.

`1 2 3 4 5 6 7 ` ` import os master_addr = os.environ.get("MASTER_ADDR", "127.0.0.1") master_port = os.environ.get("MASTER_PORT", "6006") global_rank = int(os.environ.get("RANK", -1)) local_rank = int(os.environ.get("LOCAL_RANK", -1)) world_size = int(os.environ.get("WORLD_SIZE", 1))`

* *Note ** : Connecting the machines is relatively simple, but successful training still requires all the considerations we mentioned. We recommend you look into Fabric or PyTorch Lightning which handles all other training logistics for you.

# Balance cost and time[](#balance-cost-and-time)

A key objective in multi-GPU setups is linear performance scaling. As the number of GPUs doubles, the time taken should halve. This optimizes both cost and time. Consider the following scenario:

Using a single T4 GPU instance costs $0.68 per hour, compared to $3.39 per hour for an instance with four T4 GPUs.

Add row above

Add row below

Delete row

Add column to left

Add column to right

Delete column

* *GPUs **

* *Machines **

* *Training hours **

* *Total cost **

* *Notes **

1

1

128

$87.04

$0.68 x 128

2

2

64

$87.04

$0.68 x 2 x 64

4

1

32

$108.48

$3.39 x 32

8

2

16

$108.48

$3.39 x 2 x 16

16

4

8

$108.48

$3.39 x 4 x 8

32

8

4

$108.48

$3.39 x 8 x 4

* *Ideally ** , the cost * *doesn't increase ** with more GPUs if linear scaling is achieved. Although in reality, perfect linear scaling is challenging, and costs may increase slightly with more than 8 nodes.

# Optimal developer workflow[](#optimal-developer-workflow)

These tips can save you around 60% in development costs and make your development process 6x faster.

## Develop on CPU, run on GPU[](#develop-on-cpu-run-on-gpu)

Outside of Studios, it is common to code locally, submit to a remote machine, wait for a failure, debug, and repeat. This creates a lot of wasted time and GPU hours on inefficient GPU usage.

Start your development on a CPU machine. Debug and get your model working well before you move to a GPU. Once you're confident, switch to a cheap GPU. Repeat the debugging process there until you feel confident it will scale. Once that's done, switch to a multi-GPU Studio and run your code again. This time you'll have high-confidence that the training will not fail. The final tuning you can do is to maximize VRAM usage and utilization.

https://pl-bolts-doc-images.s3.us-east-2.amazonaws.com/Docs\_Studios\_MP4/Docs\_TrainModels\_MultiGPUTraining\_OptimalFlow3.mp4

An overview of the optimal development workflow.

If your ML framework does not support changing hardware without code changes, then consider using PyTorch Lightning to pretrain or finetune your model. Now switch to 1 GPU and run the code again. Here you need to make sure nothing is breaking.

