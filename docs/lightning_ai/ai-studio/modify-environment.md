# Modify environment[](#modify-environment)

In this guide, we'll learn about environments and how Studios handle them. In short, each Studio corresponds to a single environment. This provides nice work isolation and removes a lot of the need to manage environments yourself.

## What is an environment?[](#what-is-an-environment)

On a laptop it is necessary to isolate each Python project from each other to avoid dependency conflicts. For example, project A may require pandas=1.0.0 and project B may require pandas=1.1.0. Both pandas cannot live on the same laptop, so you create 2 environments, each with a different pandas.

An environment is a kind of container that bundles all the necessary dependencies for a particular Python project.

In an ideal world, you would have a new laptop for each different project, but that is of course too expensive and impractical. In Lightning, that's how we've approached it. Think of each Studio as its own laptop with its own completely isolated environment. Studios can only have a single environment.

Tip: Watch our lecture on environments if you haven't learned these before.

https://www.youtube.com/watch?v=WHWsABk4Ejk&amp;t=2s

Our lecture on environments

# Manage environments[](#manage-environments)

## conda[](#conda)

Lightning Studios include a default conda environment that is automatically sourced into all shells, batch jobs, etc. For most use-cases, the conda environment should be the only environment in the Studio. To import an existing conda environment, use ` conda env update --file "env.yml" ` .

## uv[](#uv)

For a more advanced set-up, Lightning Studios come with ` uv ` pre-installed. You can either install in the Studio environment directly with ` uv pip ` or, if you have a ` pyproject.toml ` file, get started with ` uv sync ` .

## venv[](#venv)

Typical virtual environments should be avoided in Lightning Studios as they can cause poor performance, however, you can safely create a virtual environment with ` uv venv ` .

# Environment principles[](#environment-principles)

These are the key principles around environments with Lightning Studios.

## One Studio, one environment[](#one-studio-one-environment)

We've designed Studios to be isolated environments. Each Studio is a single environment. Install whatever packages, files, and dependencies you want. When you need to create a new environment, simply create a new Studio.


Each Studio has its own isolated environment

Select an Image

## One Studio, one task[](#one-studio-one-task)

We recommend that you set up one Studio per task. A task can mean an endpoint, a finetuning workflow, a training workflow, etc. Think about it as a microservice or a self-contained task.

For example, if I'm working on a model and have different parts of that model \(training, finetuning, data prep, etc...\), I'll set up a Studio for each of those because each step of the model pipeline requires different dependencies. The code under the hood likely still comes from a single repository hosted on Github.


Create a Studio for each step of the model pipeline

Select an Image

## Install dependencies[](#install-dependencies)

There's nothing special you need to know to install dependencies. Just do what you would do on your laptop. In a Studio, open a Studio terminal, and install whatever dependencies you need.

Use * *pip * *,* *conda * *,* *poetry * *,* *apt-get ** , or build libraries from source.


Install anything you want in your environment

Select an Image

Studios give you full control to change cuda, python versions, and more. Open the environments panel to manage more environment details.


The environment panel is below the CPU / GPU selector in the Studio environment popover

Select an Image

## Python Versions[](#python-versions)

The studio ships with Python 3.10.10 as the default version. You can select a different version of python for the studio in the environments panel, by clicking on the python version number.


The environment panel is below the CPU / GPU selector in the Studio environment popover

Select an Image

This will open the python version modal, which will allow you to select the python version to use in this studio.


Selecting the version of python to use in this studio

Select an Image

It is important to note that when you change the python version, you will have to reinstall all dependencies installed via python package managers.

## Drivers and CUDA versions[](#drivers-and-cuda-versions)

The Studio ships with a fixed NVIDIA driver. Studios also ship with CUDA pre-installed. We test quite thoroughly and pre-install the most stable version but you can install a new version using conda.

`1 ` ` conda install cudatoolkit=[X.X] `

## Environments are persistent[](#environments-are-persistent)

Persistence means that anything you install in an environment will always be there. For example, start a Studio, verify it's missing a dependency \(try cowsay\).


Cowsay isn't installed

Select an Image

Now, install cowsay.


Cowsay is now installed

Select an Image

Restart the Studio or change GPUs and you'll notice you don't need to reinstall cowsay.

This guide goes into details on [environment persistence](https://lightning.ai/docs/overview/ai-studio/environment-persistence) .

# Automate with SDK[](#automate-with-sdk)

Everything we've discussed here can be done programmatically with the lightning SDK.

`1 2 3 4 5 6 7 8 9 10 11 12 13 14 15 16 17 18 19 20 21 22 ` ` # Install the Lightning SDK # pip install lightning-sdk # login to the platform # export LIGHTNING_USER_ID=0000-0000-0000-0000-0000-0000-0000-0 # export LIGHTNING_API_KEY=0000-0000-0000-0000-0000-0000-0000-0 from lightning_sdk import Studio # Start the studio s = Studio(name="model-1-server", teamspace="model-a", user="will") print("starting Studio...") s.start() # prints Status.Running print(s.status) print(s.run("pip install cowsay")) print("Stopping Studio") s.stop() `

# FAQ[](#faq)

## Can I turn off Conda?[](#can-i-turn-off-conda)

Yes, using [Base Studios](https://lightning.ai/docs/overview/ai-studio/base-studios) \! You can define a template for launching Studios using a Base Studio, including selecting the ` Coding Environment ` to have a ` Fresh environment ` that will have a clean environment with no pre-installed tools or libraries.

