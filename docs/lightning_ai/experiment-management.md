# Experiment Management[](#experiment-management)

Lightning AI comes with a free, bundled experiment manager called LitLogger. Experiment managers let you track, compare and share ML model training runs. It keeps them organized and reproducible, providing clear visibility into model performance.


LitLogger experiment dashboard

Select an Image

## Why LitLogger[](#why-litlogger)

Without reliable experiment management, teams lose history, cannot compare experiments, and struggle to reproduce or audit their work. LitLogger solves this with a built-in, persistent experiment manager that automatically organizes every run – centralizing metrics, metadata, and artifacts so experiments can be compared, restored, and shared easily. The result is clarity of research results, faster iteration, and reproducible model development without having to pay for a standalone platform.

Key features:

  - Generous free tier

  - PyTorch optimized

  - Share with anyone

  - Granular permissions \(RBAC\)

  - Granular project management


## Quick Start[](#quick-start)

### Install[](#install)

`1 ` ` pip install litlogger`

See more details at [Installation](experiment-management/install)

### Hello World[](#hello-world)

Enable logging by adding this to ANY Python code:

`1 2 3 4 5 6 7 8 ` ` import litlogger litlogger.init() for i in range(10): litlogger.log({"my_metric": i}) litlogger.finalize()`

## APIs[](#apis)

LitLogger provides two APIs: a * *standalone API ** for any Python code, and an * *Experiment ** class for more control.

### Standalone API[](#standalone-api)

The standalone API uses [ ` litlogger.init() ` ](experiment-management/api#litlogger.init.init) and module-level functions. This is the recommended approach for most use cases.

`1 2 3 4 5 6 7 8 9 10 11 ` ` import litlogger litlogger.init( name="my-experiment", metadata={"model": "ResNet50", "lr": "0.001"}, ) for epoch in range(10): litlogger.log_metrics({"loss": 1.0 / (epoch + 1)}, step=epoch) litlogger.finalize()`

See [Standalone Usage](experiment-management/guide/standalone) for the full guide.

### Experiment[](#experiment)

[ ` litlogger.init() ` ](experiment-management/api#litlogger.init.init) returns an [ ` Experiment ` ](experiment-management/api#litlogger.experiment.Experiment) instance. You can also create one directly for full control over the experiment lifecycle.

`1 2 3 4 5 6 7 8 9 10 11 12 13 ` ` from litlogger import Experiment exp = Experiment( name="my-experiment", metadata={"model": "ResNet50", "lr": "0.001"}, ) for epoch in range(10): exp.log_metrics({"loss": 1.0 / (epoch + 1)}, step=epoch) exp.log_file("config.yaml") exp.log_model(model) exp.finalize()`

See the [API Reference](experiment-management/api) reference for all available methods.

## PyTorch Lightning Integration[](#pytorch-lightning-integration)

The [ ` LightningLogger ` ](experiment-management/api#litlogger.logger.LightningLogger) class integrates directly with the PyTorch Lightning Trainer, so every ` self.log() ` call is automatically forwarded to Lightning.ai.

`1 2 3 4 5 6 7 8 9 10 ` ` from lightning import Trainer from litlogger import LightningLogger logger = LightningLogger( name="my-experiment", metadata={"model": "ResNet50"}, ) trainer = Trainer(max_epochs=10, logger=logger) trainer.fit(model, datamodule)`

See [Lightning Integration](experiment-management/guide/lightning) for the full guide.

## View and Share Runs[](#view-and-share-runs)

All experiments are collected in the “Experiments” tab in your Teamspace.


Experiments tab in your Teamspace

Select an Image

Open an experiment detail to share with everyone or specific users.


Sharing option for experiments

Select an Image

## Home[](#home)

  - [Experiment Management](#)

  - [Install](experiment-management/install)


## Guides[](#guides)

  - [Standalone Usage](experiment-management/guide/standalone)

  - [Lightning Integration](experiment-management/guide/lightning)

  - [Logging Artifacts](experiment-management/guide/artifacts)

  - [Logging Media](experiment-management/guide/media)

  - [Examples](experiment-management/guide/examples)


## API Reference[](#api-reference)

  - [API Reference](experiment-management/api)


