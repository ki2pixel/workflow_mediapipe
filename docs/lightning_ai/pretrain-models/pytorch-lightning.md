# PyTorch Lightning[](#pytorch-lightning)

PyTorch Lightning is the deep learning framework with “batteries included” for professional AI researchers and machine learning engineers who need maximal flexibility while super-charging performance at scale.

Lightning organizes PyTorch code to remove boilerplate and unlock scalability.

For [pip](https://pypi.org/project/pytorch-lightning/) users

`1 ` ` pip install lightning`

For [conda](https://anaconda.org/conda-forge/pytorch-lightning) users

`1 ` ` conda install lightning -c conda-forge`

Or read the [advanced install guide](https://lightning.ai/docs/pytorch/stable/starter/installation.html)

A LightningModule enables your PyTorch nn.Module to play together in complex ways inside the training\_step \(there is also an optional validation\_step and test\_step\).

`1 2 3 4 5 6 7 8 9 10 11 12 13 14 15 16 17 18 19 20 21 22 23 24 25 26 27 28 29 30 31 32 33 34 35 36 37 ` ` #import os from torch import optim, nn, utils, Tensor from torchvision.datasets import MNIST from torchvision.transforms import ToTensor import lightning as L # define any number of nn.Modules (or use your current ones) encoder = nn.Sequential(nn.Linear(28 * 28, 64), nn.ReLU(), nn.Linear(64, 3)) decoder = nn.Sequential(nn.Linear(3, 64), nn.ReLU(), nn.Linear(64, 28 * 28)) # define the LightningModule class LitAutoEncoder(L.LightningModule): def * *init * *(self, encoder, decoder): super(). * *init * *() self.encoder = encoder self.decoder = decoder def training_step(self, batch, batch_idx): # training_step defines the train loop. # it is independent of forward x, _ = batch x = x.view(x.size(0), -1) z = self.encoder(x) x_hat = self.decoder(z) loss = nn.functional.mse_loss(x_hat, x) # Logging to TensorBoard (if installed) by default self.log("train_loss", loss) return loss def configure_optimizers(self): optimizer = optim.Adam(self.parameters(), lr=1e-3) return optimizer # init the autoencoder autoencoder = LitAutoEncoder(encoder, decoder)`

Lightning supports ANY iterable \( [ ` DataLoader ` ](https://pytorch.org/docs/stable/data.html#torch.utils.data.DataLoader) , numpy, etc…\) for the train/val/test/predict splits.

`1 2 3 ` ` # setup data dataset = MNIST(os.getcwd(), download=True, transform=ToTensor()) train_loader = utils.data.DataLoader(dataset)`

The Lightning [Trainer](https://lightning.ai/docs/pytorch/stable/common/trainer.html) “mixes” any [LightningModule](https://lightning.ai/docs/pytorch/stable/common/lightning_module.html) with any dataset and abstracts away all the engineering complexity needed for scale.

`1 2 3 4 ` ` # train the model (hint: here are some helpful Trainer arguments for rapid idea iteration) trainer = L.Trainer(limit_train_batches=100, max_epochs=1) trainer.fit(model=autoencoder, train_dataloaders=train_loader) `

The Lightning [Trainer](https://lightning.ai/docs/pytorch/stable/common/trainer.html) automates [40+ tricks](https://lightning.ai/docs/pytorch/stable/common/trainer.html#trainer-flags) including:

  - Epoch and batch iteration

  - optimizer.step\(\)

  - Calling of

  - Checkpoint Saving and Loading

  - Tensorboard \(see

  - Multi-GPU

  - TPU

  - 16-bit precision AMP


Once you’ve trained the model you can export to onnx, torchscript and put it into production or simply load the weights and run predictions.

`1 2 3 4 5 6 7 8 9 10 11 12 ` ` # load checkpoint checkpoint = "./lightning_logs/version_0/checkpoints/epoch=0-step=100.ckpt" autoencoder = LitAutoEncoder.load_from_checkpoint(checkpoint, encoder=encoder, decoder=decoder) # choose your trained nn.Module encoder = autoencoder.encoder encoder.eval() # embed 4 fake images! fake_image_batch = torch.rand(4, 28 * 28, device=autoencoder.device) embeddings = encoder(fake_image_batch) print("⚡" * 20, "\nPredictions (4 image embeddings):\n", embeddings, "\n", "⚡" * 20)`

If you have tensorboard installed, you can use it for visualizing experiments.

Run this on your commandline and open your browser to http://localhost:6006/

`1 ` ` tensorboard --logdir .`

Enable advanced training features using Trainer arguments. These are state-of-the-art techniques that are automatically integrated into your training loop without changes to your code.

`1 2 3 4 5 6 7 8 9 10 11 12 13 14 15 16 17 18 19 20 21 22 23 ` ` # train on 4 GPUs trainer = L.Trainer( devices=4, accelerator="gpu", ) # train 1TB+ parameter models with Deepspeed/fsdp trainer = L.Trainer( devices=4, accelerator="gpu", strategy="deepspeed_stage_2", precision=16 ) # 20+ helpful flags for rapid idea iteration trainer = L.Trainer( max_epochs=10, min_epochs=5, overfit_batches=1 ) # access the latest state of the art techniques trainer = L.Trainer(callbacks=[StochasticWeightAveraging(...)]) `

Lightning’s core guiding principle is to always provide maximal flexibility without ever hiding any of the PyTorch. Lightning offers 5 added degrees of flexibility depending on your project’s complexity.


Select an Image

Inject custom code anywhere in the Training loop using any of the 20+ methods \( [Hooks](https://lightning.ai/docs/pytorch/stable/common/lightning_module.html#lightning-hooks) \) available in the LightningModule.

`1 2 3 ` ` class LitAutoEncoder(L.LightningModule): def backward(self, loss): loss.backward()`

If you have multiple lines of code with similar functionalities, you can use callbacks to easily group them together and toggle all of those lines on or off at the same time.

`1 ` ` trainer = Trainer(callbacks=[AWSCheckpoints()])`

