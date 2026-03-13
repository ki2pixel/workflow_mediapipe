# TorchMetrics[](#torchmetrics)

TorchMetrics is a collection of 100+ PyTorch metrics implementations and an easy-to-use API to create custom metrics. It offers:

  - A standardized interface to increase reproducibility

  - Reduces Boilerplate

  - Distributed-training compatible

  - Rigorously tested

  - Automatic accumulation over batches

  - Automatic synchronization between multiple devices


You can use TorchMetrics in any PyTorch model, or within [PyTorch Lightning](https://lightning.ai/docs/pytorch/stable/) to enjoy additional features:

  - This means that your data will always be placed on the same device as your metrics.

  - Native support for logging metrics in Lightning to reduce even more boilerplate.


You can install TorchMetrics using pip or conda:

`1 2 3 4 5 ` ` # Python Package Index (PyPI) pip install torchmetrics # Conda conda install -c conda-forge torchmetrics `

Eventually if there is a missing PyTorch wheel for your OS or Python version you can simply compile [PyTorch from source](https://github.com/pytorch/pytorch) :

`1 2 3 4 5 6 7 8 9 ` ` # Optional if you do not need compile GPU support export USE_CUDA=0 # just to keep it simple # you can install the latest state from master pip install git+https://github.com/pytorch/pytorch.git # OR set a particular PyTorch release pip install git+https://github.com/pytorch/pytorch.git@<release-tag> # and finalize with installing TorchMetrics pip install torchmetrics `

## Using TorchMetrics[](#using-torchmetrics)

Similar to [torch.nn](https://pytorch.org/docs/2.6/nn) , most metrics have both a class-based and a functional version. The functional versions implement the basic operations required for computing each metric. They are simple python functions that as input take [torch.tensors](https://pytorch.org/docs/2.6/tensors.html) and return the corresponding metric as a ` torch.tensor ` . The code-snippet below shows a simple example for calculating the accuracy using the functional interface:

`1 2 3 4 5 6 7 8 9 10 ` ` import torch # import our library import torchmetrics # simulate a classification problem preds = torch.randn(10, 5).softmax(dim=-1) target = torch.randint(5, (10,)) acc = torchmetrics.functional.accuracy(preds, target, task="multiclass", num_classes=5) `

Nearly all functional metrics have a corresponding class-based metric that calls it a functional counterpart underneath. The class-based metrics are characterized by having one or more internal metrics states \(similar to the parameters of the PyTorch module\) that allow them to offer additional functionalities:

  - Accumulation of multiple batches

  - Automatic synchronization between multiple devices

  - Metric arithmetic


The code below shows how to use the class-based interface:

`1 2 3 4 5 6 7 8 9 10 11 12 13 14 15 16 17 18 19 20 21 22 23 ` ` import torch # import our library import torchmetrics # initialize metric metric = torchmetrics.classification.Accuracy(task="multiclass", num_classes=5) n_batches = 10 for i in range(n_batches): # simulate a classification problem preds = torch.randn(10, 5).softmax(dim=-1) target = torch.randint(5, (10,)) # metric on current batch acc = metric(preds, target) print(f"Accuracy on batch {i}: {acc}") # metric on all batches using custom accumulation acc = metric.compute() print(f"Accuracy on all data: {acc}") # Resetting internal state such that metric ready for new data metric.reset() `

Implementing your own metric is as easy as subclassing a [ ` torch.nn.Module ` ](https://pytorch.org/docs/stable/generated/torch.nn.Module.html#torch.nn.Module) . Simply, subclass [ ` Metric ` ](https://lightning.ai/docs/torchmetrics/stable/references/metric.html#torchmetrics.Metric) and do the following:

  1. Implement ` * *init ** ` where you call ` self.add_state ` for every internal state that is needed for the metrics computations

  2. Implement ` update ` method, where all logic that is necessary for updating metric states go

  3. Implement ` compute ` method, where the final metric computations happens


For practical examples and more info about implementing a metric, please see this [page](https://lightning.ai/docs/torchmetrics/stable/pages/implement.html#implement) .

TorchMetrics provides a [Devcontainer](https://code.visualstudio.com/docs/remote/containers) configuration for [Visual Studio Code](https://code.visualstudio.com/) to use a [Docker container](https://www.docker.com/) as a pre-configured development environment. This avoids struggles setting up a development environment and makes them reproducible and consistent. Please follow the [installation instructions](https://code.visualstudio.com/docs/remote/containers#_installation) and make yourself familiar with the [container tutorials](https://code.visualstudio.com/docs/remote/containers-tutorial) if you want to use them. In order to use GPUs, you can enable them within the ` .devcontainer/devcontainer.json ` file.

