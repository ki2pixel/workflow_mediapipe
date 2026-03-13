# Training guide[](#training-guide)

Get the most out of Lightning for * *pretraining * *or * *finetuning ** models and save on cloud costs with this developer workflow guide.

Watch this in-depth video to understand the full development process, applicable for both pretraining and finetuning.

https://youtu.be/aPzbR1s1O\_8

Pretrain a 3B LLM from scratch.

# Choose pretrain vs finetune[](#choose-pretrain-vs-finetune)

Both pretraining and finetuning follow this workflow. Pretraining might take more effort but the core concept remains the same.

If you're new to Machine Learning and wondering about the difference between pretraining and finetuning, here's a quick primer. Otherwise, you might want to skip this part.

Pretraining and finetuning use the same Lightning tools, differing mainly in code. Think of pretraining as cooking from scratch and finetuning as warming up a ready-made meal. Although starting from scratch might be more time-consuming and costly, it often yields better outcomes.

Differences include:

Add row above

Add row below

Delete row

Add column to left

Add column to right

Delete column

Tooling needed

Pretraining

Finetuning

Done from a Studio

✅

✅

Can be done on 1 GPU\*

✅ \(for small models\)

✅

Can be done on multiple GPUs

✅ \(for small models\)

✅

Requires multi-node

✅ \(for large models\)

🚫 not often

Can be done with a small dataset

🚫

✅

The challenge in finetuning lies in determining which weights to adjust. There are many techniques \( [LoRA](https://github.com/Lightning-AI/litgpt/blob/wip/tutorials/finetune_lora.md) , [QLoRA](https://github.com/Lightning-AI/litgpt/blob/wip/tutorials/finetune_lora.md) , [Adapter](https://github.com/Lightning-AI/litgpt/blob/wip/tutorials/finetune_adapter.md) , etc...\). However, those are changes done in your code and don't affect the Studio or tools used.

# Setup[](#setup)

In this phase set up your Studio and make sure your data is optimized for training. If you are new to ML or want ready-to-go recipes, start from one of our [prebuilt studio templates](https://lightning.ai/studios?section=training) . Starting from a template can save you wezapped of setup and training costs.

## 0\. Optimize the dataset[](#0-optimize-the-dataset)

This step applies to both pretraining and finetuning.

Before training, make sure you followed our guide to [setup and optimize your data for training](https://lightning.ai/docs/overview/prep-data) . If your dataset is small \(<50 GB\) and with a few files, then optimizing the dataset probably won't do much for you since the data will not bottleneck training.

Add row above

Add row below

Delete row

Add column to left

Add column to right

Delete column

* *Optimize dataset? **

Small dataset \(<50 GB\)

Not needed

Datasets 50GB+

✅ Recommended

Many small files \(100,000+\)

✅ Recommended

## 1\. Setup Studio on CPU[](#1-setup-studio-on-cpu)

This step applies to both pretraining and finetuning.

Whether you are pretraining or finetuning, the first step is to set up the Studio. Do this on a CPU Studio so you don't spend valuable setup time on expensive GPUs.

If you start from a Studio template, then everything has already been taken care of for you.

https://pl-bolts-doc-images.s3.us-east-2.amazonaws.com/Docs\_Studios\_MP4/TrainModel\_DevWorkflowForTraining\_DuplicateTemplate2.mp4

Start from a Studio template.

Typical setup involves:

  - Get the code on a Studio \(git clone, etc...\)

  - Installing requirements or building a docker image

  - Upload, connect data, make it fast for cloud usage \(see Step 0\)

  - etc...


Setting up code for model training can have a lot of moving parts. We recommend you start from one of our [pretraining templates](https://lightning.ai/studios?query=pret) or [finetuning templates](https://lightning.ai/studios?query=finet) .

https://pl-bolts-doc-images.s3.us-east-2.amazonaws.com/Docs\_Studios\_MP4/TrainModel\_DevWorkflowForTraining\_Step1SetUpStudio.mp4

When creating a Studio for training, select a template for pretraining or finetuning

# Iterate[](#iterate)

With your Studio and data ready, focus on iterations to refine your model before scaling up.

## 2\. Tune on an affordable GPU[](#2-tune-on-an-affordable-gpu)

This step applies to both pretraining and finetuning.

Next step is to find the right settings \(hyperparameters\) for your task. This is usually the batch size, learning rate, etc...

During this stage, we are usually trying to figure out the optimal settings for your model so that the model fits in GPU memory, and trains the fastest. Usually, this is done by changing the batch size, learning rate and other settings. For example in LLM finetuning, the context\_window can have a big impact here as well.

The parameters that need to be changed, vary from model to model and task to task. The video at the beginning of this page does an in-depth deep dive into the tuning process. This guide here, discusses general principles of the impact that different hyperparameters have:

https://pl-bolts-doc-images.s3.us-east-2.amazonaws.com/Docs\_Studios\_MP4/TrainModel\_DevWorkflowForTraining\_Step2TryOnCheapGPU.mp4

A deep dive into the tuning process.

## 3\. Hyperparameter search[](#3-hyperparameter-search)

This step applies to both pretraining and finetuning.

Finding the right set of hyperparameters is crucial for efficient model training. Good hyperparameters, in particular the ` learning_rate ` and its scheduling, can mean the difference between a model that trains well and a model that doesn't.

The following image illustrates how different learning rates impact training speed and outcome.


Tracking metrics model running with different learning rates.

Select an Image

For example, in the image above, you see that multiple learning rates affect the speed and final value of a loss curve. A high learning rate \(on the left\) goes down faster, but does not go as low as others. A super-slow learning rate can take forever to get to the same level. The best setting is a learning rate that gets the loss low fast without compromising on the global minimum value \(where the loss is the lowest\).

Read this guid on [hyperparameter tuning](https://lightning.ai/lightning-ai/environments/run-a-hyperparameter-sweep?view=public§ion=featured&query=hyperparameter&tab=overview) for more details.

# Scale[](#scale)

In this phase, you want to scale your model once you feel confident you've tuned your model settings already on cheaper hardware.

## 4\. Graduate to powerful GPUs[](#4-graduate-to-powerful-gpus)

This may not be necessary for all finetuning tasks. Small models or datasets might only require affordable GPUs.

https://pl-bolts-doc-images.s3.us-east-2.amazonaws.com/Docs\_Studios\_MP4/TrainModel\_DevWorkflowForTraining\_Step4ScaleToExpensiveGPUs.mp4

Scale to expensive GPUs to speed up training. Inexpensive GPUs may not be cheaper.

For less than $7, [this example Studio](https://lightning.ai/lightning-ai/studios/instruction-finetuning-tinyllama-1-1b-llm) finetunes a 1.1B LLM model in * *3.5 hours * *.

In this step, you can likely make the model faster by increasing the batch size \(which goes through the data faster\), but you'll need GPUs with more RAM. Even though something like an H100 is more expensive per hour, it can ultimately be cheaper because it has to run for less time.


Finetuning quickly on expensive GPUs can be cheaper than using cheap GPUs for longer.

Select an Image

The result is that a GPU that costs more per hour can finish training faster, which in turn uses fewer hours and saves more money.


Finetuning quickly on expensive GPUs can be cheaper than using cheap GPUs for longer.

Select an Image

## 5\. Use multi-node \(optional\)[](#5-use-multi-node-optional)

This step is usually not required for finetuning. It is also important you don't jump straight to this step because you will waste a lot of money and time on failed model runs. Iterate between steps 2-4 until you're happy with your model before scaling to multi-node.

If your model is very large and does not fit into a single machine \(likely LLMs over 3B params\), then you'll likely need to enable multi-node training. Multi-node training distributes a model across different machines.


Loop between steps 2 and 4 before progressing to multi-node training.

Select an Image

https://pl-bolts-doc-images.s3.us-east-2.amazonaws.com/Docs\_Studios\_MP4/TrainModel\_DevWorkflowForTraining\_Step5ScaleToMultinode.mp4

Multi-node training distributes model training across multiple machines.

Multi-node can both enable large-model training, but it can also speed up training on smaller models. The challenge is that doing multi-node training correctly is out of reach for most developers. We recommend you use [PyTorch Lightning](https://lightning.ai/docs/pytorch/stable/?referrer=platform-docs) or [Lightning Fabric](https://lightning.ai/docs/fabric/stable/) , where multi-node training is 100% handled for you.

With [PyTorch Lightning](https://lightning.ai/docs/pytorch/stable/?referrer=platform-docs) or [Lightning Fabric](https://lightning.ai/docs/fabric/stable/) , if you can train on a CPU, you can train on multi-node with zero code changes.

Here's an example that runs on a CPU Studio, then run it on a 4-GPU Studio, then run it across 2 machines.

https://pl-bolts-doc-images.s3.us-east-2.amazonaws.com/app-2/scale\_to\_mmt.mp4

Scaling from CPU to 4-GPU.

Run this code yourself to see that there are no code changes required.

`1 2 3 4 5 6 7 8 9 10 11 12 13 14 15 16 17 18 19 20 21 22 23 24 25 26 27 28 29 30 31 32 33 34 35 36 37 38 39 40 41 42 43 44 45 46 47 48 49 50 ` ` # main.py # ! pip install torchvision import torch, torch.nn as nn, torch.utils.data as data, torchvision as tv, torch.nn.functional as F import lightning as L # -------------------------------- # Step 1: Define a LightningModule # -------------------------------- # A LightningModule (nn.Module subclass) defines a full *system* # (ie: an LLM, diffusion model, autoencoder, or simple image classifier). class LitAutoEncoder(L.LightningModule): def * *init * *(self): super(). * *init * *() self.encoder = nn.Sequential(nn.Linear(28 * 28, 128), nn.ReLU(), nn.Linear(128, 3)) self.decoder = nn.Sequential(nn.Linear(3, 128), nn.ReLU(), nn.Linear(128, 28 * 28)) def forward(self, x): # in lightning, forward defines the prediction/inference actions embedding = self.encoder(x) return embedding def training_step(self, batch, batch_idx): # training_step defines the train loop. It is independent of forward x, y = batch x = x.view(x.size(0), -1) z = self.encoder(x) x_hat = self.decoder(z) loss = F.mse_loss(x_hat, x) self.log("train_loss", loss) return loss def configure_optimizers(self): optimizer = torch.optim.Adam(self.parameters(), lr=1e-3) return optimizer # ------------------- # Step 2: Define data # ------------------- dataset = tv.datasets.MNIST(".", download=True, transform=tv.transforms.ToTensor()) train, val = data.random_split(dataset, [55000, 5000]) # ------------------- # Step 3: Train # ------------------- autoencoder = LitAutoEncoder() trainer = L.Trainer() trainer.fit(autoencoder, data.DataLoader(train), data.DataLoader(val))`

# Deploy[](#deploy)

Once the model has been trained, you'll have all the checkpoints you need on the teamspace Drive. There's no need to store checkpoints on different systems, you can simply access the checkpoints from any other Studio.

https://pl-bolts-doc-images.s3.us-east-2.amazonaws.com/Docs\_Studios\_MP4/TrainModels\_DevWorkflowForTraining\_DeploymentPhase.mp4

Checkpoints on a trained model can be accessed anywhere in the same teamspace.

