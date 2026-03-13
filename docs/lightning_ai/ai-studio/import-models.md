# Import models[](#import-models)

This section describes various ways to get model checkpoints and code into Studios. In principle, do exactly the same that you would do on your laptop today.

# Import within Studios[](#import-within-studios)

Use any of these methods to import models from the Studio web app.

## Upload to Drive[](#upload-to-drive)

Click on the * *Drive icon * *>* *Add data ** , select the checkpoint file and press upload.

https://pl-bolts-doc-images.s3.us-east-2.amazonaws.com/Docs\_Studios\_MP4/Import\_models-UploadToDrive.mp4

Upload your model checkpoint file to your Studio Drive.

The model will now be accessible from any Studio in the teamspace.

https://pl-bolts-doc-images.s3.us-east-2.amazonaws.com/Docs\_Studios\_MP4/Import\_models-UploadToDrive\_AvailableFromStudio.mp4

Once your model is uploaded, you can access the model from any Studio in the teamspace.

## Upload to VSCode or Jupyter[](#upload-to-vscode-or-jupyter)

Drag and drop the checkpoint file into the VSCode or Jupyter interface which will automatically upload the files.

https://pl-bolts-doc-images.s3.us-east-2.amazonaws.com/Docs\_Studios\_MP4/Import\_models-UploadtoVSCodeorJupyter.mp4

Drag and drop your checkpoint file directly into VSCode \(or Jupyter\).

The model will now be available to access from any Studio in the teamspace. For more on Lightning SDK, read our [in-depth guide](https://lightning.ai/docs/overview/Studios/sdk) .

## Import from Hugging Face hub[](#import-from-hugging-face-hub)

This example shows how to download a model from the Hugging Face hub via the Studio terminal.

https://pl-bolts-doc-images.s3.us-east-2.amazonaws.com/Docs\_Studios\_MP4/Import\_models-HF.mp4

Use your Studio terminal to download models from model hubs like Hugging Face.

## Import from Github[](#import-from-github)

Find the repository that has the model checkpoints and clone the repo.

https://pl-bolts-doc-images.s3.us-east-2.amazonaws.com/Docs\_Studios\_MP4/Import\_models-GitHub.mp4

Git clone GitHub repos with model checkpoints into your Studio.

## Import using Studio terminal[](#import-using-studio-terminal)

Use the Studio terminal to download any file \(like model checkpoints\) using the curl command.

https://pl-bolts-doc-images.s3.us-east-2.amazonaws.com/Docs\_Studios\_MP4/Import\_models-viaStudioTerminal-Curl.mp4

Use the curl command in the Studio terminal to download files and model checkpoints.

# Import from outside Studios[](#import-from-outside-studios)

Use these methods to upload models from outside Lightning programatically.

## Upload via CLI[](#upload-via-cli)

Use the Lightning [SDK](https://lightning.ai/docs/overview/developers/sdk) to upload the model checkpoint into the teamspace.

https://pl-bolts-doc-images.s3.us-east-2.amazonaws.com/Docs\_Studios\_MP4/Import\_models-LocalTerminal2.mp4

Upload your checkpoint file into your Studio via terminal.

