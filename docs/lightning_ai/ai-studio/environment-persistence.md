# Environment persistence[](#environment-persistence)

Studios persist their environments when sleeping and switching machines. Jobs use forks of the environment so that the environment you develop is the same you scale.

https://pl-bolts-doc-images.s3.us-east-2.amazonaws.com/Docs\_Studios\_MP4/Docs\_Studios\_ChangeGPUs\_PersistentDependencies.mp4

Studio environments persist when switching machines or sleeping

There are a lot of nuances and details about how we do persistency that we will not cover in this guide. However, we will discuss the common questions that cover the main use cases.

## Filesystem[](#filesystem)

Everything in the Studio home \( ` ~`, ` /teamspace/studios/this_studio ` \) is persisted except for ` node_modules ` , which should be recreated when needed. Download any files, build packages and whatever else you want\!

## Python environment[](#python-environment)

Any packages you install or build are persisted. You can install packages in editable mode, edit your site-packages, and anything else you might need.

https://pl-bolts-doc-images.s3.us-east-2.amazonaws.com/Docs\_Studios\_MP4/Docs\_Studios\_EnvironmentPersistency\_InstallPackages.mp4

Install your packages; they'll persist

Note that we don't allow creating additional environments or virtual environments within the Studio. If you need to create a new environment, start a new Studio.

https://pl-bolts-doc-images.s3.us-east-2.amazonaws.com/Docs\_Studios\_MP4/Docs\_Studios\_EnvironmentPersistency\_InstallPackages2-NewStudio.mp4

Need a new environment? Start a new studio\!

## VSCode settings[](#vscode-settings)

Any extensions installed, or changes you make to your VSCode on the Studio will apply to the VSCode across ALL your Studios. For example, if you install [Github Copilot](https://marketplace.visualstudio.com/items?itemName=GitHub.copilot) , it will be available in all your Studios.

## JupyterLab settings[](#jupyterlab-settings)

JupyterLab settings are not persisted.

## System packages[](#system-packages)

Any system packages you install will be persisted. We recommend you install everything via * *apt-get * *.

https://pl-bolts-doc-images.s3.us-east-2.amazonaws.com/Docs\_Studios\_MP4/Docs\_Studios\_EnvironmentPersistency\_InstallSystemPackages.mp4

Use apt-get to install, update, and remove software packages

If you install packages in non standard ways or place them in non standard locations, there is a chance they will not be persisted. This is for your security.

If you rely additional binaries that aren't available through * *apt-get ** , we recommend placing them somewhere in your Studio home \( ` ~`, ` /teamspace/studios/this_studio ` \) and adding them to the ` PATH ` in your ` .zshrc ` , ` .bashrc ` , ` .profile ` , or similar. For example:

`1 ` ` export PATH="/teamspace/studios/this_studio/bin:${PATH}"`

## Docker images[](#docker-images)

Feel free to build docker images on the Studio. They are currently not persisted, if you are interested in this feature please reach out to us at [support@lightning.ai](mailto:support@lightning.ai) .

