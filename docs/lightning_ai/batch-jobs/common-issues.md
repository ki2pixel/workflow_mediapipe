# Common issues[](#common-issues)

This guide addresses common challenges you might encounter when using Batch Jobs and provides tips to resolve them.


## Slow Job start[](#slow-job-start)

When a job originates from a Studio, it uses the full Studio environment, including all files. The startup time is directly proportional to the number of files in the Studio.

* *Solution: **

  - Move large or unnecessary files to dedicated S3 or EFS folders in the Teamspace drive.

  - Ensure the Studio environment contains only essential files required for the job.


Optimizing the environment will significantly reduce job startup times.

## Job failure[](#job-failure)

Jobs can fail for various reasons, but the most common cause is bugs in the user code.

* *Solution: **

  - Iterate in Studio First: Debug and test your code interactively in Studio until it runs successfully.

  - Check Logs: Review job logs for error details to pinpoint the issue.

  - Platform Support: If you suspect the issue lies with the platform.


## Environment snapshotting[](#environment-snapshotting)

When submitting a job from a Studio, the entire Studio environment is snapshot, including code, data, and dependencies.

* *Considerations: **

  - Ensure the environment is clean and optimized for better performance.

  - Remove unnecessary files or dependencies to prevent bloated snapshots and slower job execution.


## Resuming a failed training job[](#resuming-a-failed-training-job)

If you are using Pytorch Lightning to train a model, it stores all training artifacts in a directory named ` lightning_logs/version_<number> ` which will be located in the artifacts directory for the job. This directory contains the model checkpoints in the ` checkpoints ` directory, and a tensorboard training log file for the training run.

## Multi-Machine Setup[](#multi-machine-setup)

When submitting a multi-machine job, make sure your job uses the default [PyTorch environment variables](https://pytorch.org/docs/2.5/distributed.html#environment-variable-initialization) to setup a distributed connection. Have a look at our [PyTorch Lightning documentation](https://lightning.ai/docs/pytorch/stable/levels/intermediate_level_14.html) for more details.

PyTorch Lightning automatically detects the environment, the number and type of accelerators available and [sets up the connection accordingly](https://lightning.ai/docs/pytorch/stable/clouds/lightning_ai.html) .

