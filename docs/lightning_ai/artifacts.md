# Artifacts[](#artifacts)

In ML engineering, managing and accessing generated files, known as _artifacts_ , is a critical task. Lightning simplifies this process by providing a unified filesystem across Studios, the * *_teamspace drive_ ** , for easy artifact management.

## What is an artifact[](#what-is-an-artifact)

At its core, an artifact is a generated file crucial in AI development projects. Examples of artifacts include:

Simply put, an artifact is a file. In the context of AI development, an artifact can be:

  - Model checkpoints

  - Generated images or text

  - Various script-generated files


Artifact sharing is at the core of the development and deployment process in AI projects.

## Share artifacts between Studios[](#share-artifacts-between-studios)

Within Lightning, all Studios share a filesystem: the teamspace drive. This setup facilitates the seamless transfer of artifacts between Studios. Let's say you finetune a model on one Studio and want to deploy that model on a different Studio. To do this, you'd need to figure out how to get the model checkpoint to the deployment Studio.

In Lightning, transferring artifacts is as simple as it is on your laptop. Simply copy the file over or symlink it.

https://pl-bolts-doc-images.s3.us-east-2.amazonaws.com/Docs\_Studios\_MP4/Docs\_PrepData\_CreateADatasetInAStudio.mp4

Studios share artifacts through their shared filesystem, their teamspace drive

## Download artifacts[](#download-artifacts)

For those integrating Lightning Studios with external production pipelines or simply needing to transfer files out, the teamspace drive offers a straightforward download capability mimicking a typical desktop experience.

https://pl-bolts-doc-images.s3.us-east-2.amazonaws.com/Docs\_Studios\_MP4/Docs\_PrepData\_DownloadArtifacts.mp4

Download artifacts, like checkpoints, form your teamspace drive

Automate file downloads with the SDK

`1 2 3 4 5 6 7 8 ` ` # export LIGHTNING_USER_ID=000000-000000-000000-00000-000000000 # export LIGHTNING_API_KEY=111111-111111-111111-11111-111111111 from lightning_sdk import Studio studio = Studio("studio-2", teamspace="research", org="lightning-ai") studio.download_file("ptl_default.ckpt")`

## Export artifacts to S3[](#export-artifacts-to-s3)

You might need artifacts in other S3 buckets that are not connected to Lightning. To move them there, use the AWS CLI:

https://pl-bolts-doc-images.s3.us-east-2.amazonaws.com/Docs\_Studios\_MP4/Docs\_PrepData\_ExportArtifactstoS3-2.mp4

Use AWS CLI to export artifacts to external S3 buckets

## View and explore artifacts[](#view-and-explore-artifacts)

The teamspace drive provides a robust platform to explore artifacts. Drive is optimized to display massive, multi-terabyte datasets without problems. Drive outperforms VSCode when you need to explore large datasets.

https://pl-bolts-doc-images.s3.us-east-2.amazonaws.com/Docs\_Studios\_MP4/Docs\_PrepData\_ViewAndExploreArtifacts.mp4

View and explore artifacts across your teamspace via UI or CLI

