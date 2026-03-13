# Lightning Fabric[](#lightning-fabric)

Fabric is the fast and lightweight way to scale PyTorch models without boilerplate. Convert PyTorch code to Lightning Fabric in 5 lines and get access to SOTA distributed training features \(DDP, FSDP, DeepSpeed, mixed precision and more\) to scale the largest billion-parameter models.

Pip users

`1 ` ` pip install lightning`

Conda users

`1 ` ` condainstalllightning-cconda-forge`

Or read the [advanced install guide](https://lightning.ai/docs/fabric/stable/fundamentals/installation.html) .

You can find the list of supported PyTorch versions in our [compatibility matrix](https://lightning.ai/docs/pytorch/stable/versioning.html#compatibility-matrix) .


Select an Image

Fabric differentiates itself from a fully-fledged trainer like Lightning’s [Trainer](https://lightning.ai/docs/pytorch/stable/common/trainer.html) in these key aspects:

Fast to implement There is no need to restructure your code: Just change a few lines in the PyTorch script and you’ll be able to leverage Fabric features.

Maximum Flexibility Write your own training and/or inference logic down to the individual optimizer calls. You aren’t forced to conform to a standardized epoch-based training loop like the one in Lightning [Trainer](https://lightning.ai/docs/pytorch/stable/common/trainer.html) . You can do flexible iteration based training, meta-learning, cross-validation and other types of optimization algorithms without digging into framework internals. This also makes it super easy to adopt Fabric in existing PyTorch projects to speed-up and scale your models without the compromise on large refactors. Just remember: With great power comes a great responsibility.

Maximum Control The Lightning [Trainer](https://lightning.ai/docs/pytorch/stable/common/trainer.html) has many built-in features to make research simpler with less boilerplate, but debugging it requires some familiarity with the framework internals. In Fabric, everything is opt-in. Think of it as a toolbox: You take out the tools \(Fabric functions\) you need and leave the other ones behind. This makes it easier to develop and debug your PyTorch code as you gradually add more features to it. Fabric provides important tools to remove undesired boilerplate code \(distributed, hardware, checkpoints, logging, …\), but leaves the design and orchestration fully up to you.

