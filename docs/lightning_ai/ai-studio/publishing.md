# Publishing[](#publishing)

Publishing allows you to share Studios with anyone on the internet or inside your organization.


Public Studio templates.

Select an Image

# What is publishing[](#what-is-publishing)

A published Studio can be duplicated by a user in a few minutes. Duplicating a Studio will create an exact copy of the environment including all dependencies, files, and data. A user who duplicates will not need to install anything; everything will just work out of the box.

https://pl-bolts-doc-images.s3.us-east-2.amazonaws.com/Docs\_Studios\_MP4/Docs\_Studios\_What+is+Publishing.mp4

How to duplicate a studio to your Lightning account.

# How to publish[](#how-to-publish)

To publish a Studio, press "publish" at the top right of the Studio and follow the instructions. To make it public to everyone on the internet, choose "Lightning community". Otherwise, choose the organization you'd like to publish to. Only members of this organization will be able to view and duplicate the Studio.

https://pl-bolts-doc-images.s3.us-east-2.amazonaws.com/Docs\_Studios\_MP4/Docs\_Studios\_HowtoPublish.mp4

Publish to the internal library to share Studio templates.

## Sharing on Github[](#sharing-on-github)

You can also generate an "Open in Studio" Github badge to share with a wider audience. Publish your Studio and generate a badge on the Studio detail page in the community.


https://pl-bolts-doc-images.s3.us-east-2.amazonaws.com/Docs\_Studios\_MP4/Docs\_Studios\_SharingOnGitHub.mp4

Publish your studio to generate a badge to embed on GitHub and more.

## Hiding files[](#hiding-files)

When you publish a Studio, you will also publish all the data that is in that Studio. By default, the community will be able to browse those files directly from the Studio template page. Toggle "Hide files" on to disable this for a cleaner landing page.


Increase engagement by displaying files for an easier browsing experience.

Select an Image

# Advantages[](#advantages)

## Share reproducible AI systems[](#share-reproducible-ai-systems)

The main use case for publishing is to share end-to-end, reproducible AI systems. Sharing a Github repo and a docker file is usually not enough. There are a lot of nuances related to AI development such as access to the data, special build steps for libraries like CUDA, or even environment variables that must be set for AI systems to be reproducible.


Studios collect and connect other tools and services for reproducibility.

Select an Image

Published Studios allow the user who duplicates to get an exact copy of all environment details including, code, data, environment variables, machine specs, and even the cluster specs. For example, if you [duplicate this Studio](https://lightning.ai/lightning-ai/studios/pretrain-llms-tinyllama-1-1b) , it will have everything needed to pretrain a model on 64+ GPUs.


Click "Run" to duplicate the Studio.

Select an Image

## Onboard new developers[](#onboard-new-developers)

One use case for publishing is to onboard new team members. We recommend that organizations create a library of published Studios that new members can duplicate to immediately get up and running. This can cut onboarding times from weeks to hours.


Studios as onboarding tools.

Select an Image

## Build a private Studio library[](#build-a-private-studio-library)


Private org Studio templates.

Select an Image

Organizations can create an internal library of Studios that are visible to all organization members. Use this to share models, datasets, reproducible AI systems, and more.

## Use case for consultants[](#use-case-for-consultants)

Published Studios are a simple way to deliver POCs \(proof of concepts\) or finished projects to customers. Simply build a Studio, publish it and have the customer duplicate it into their Lightning account and run on their private VPC.

https://pl-bolts-doc-images.s3.us-east-2.amazonaws.com/Docs\_Studios\_MP4/Docs\_Studios\_Publishing\_UseCaseForConsultants.mp4

Share a Studio as a POC with clients.

# Publishing vs GitHub[](#publishing-vs-github)

The traditional way to ask people to reproduce something is to send a GitHub link, a docker image and requirements to install. Even then, it is highly likely the person won't be able to get whatever you sent them working.

* *Studios solve this problem * *. To share something you are working on, simply publish the Studio and share the link with the other person. They just need to run the published Studio. In a few minutes they'll have a fully working version of what you wanted to share.

A published Studio remembers the environment, installed packages, code, data and everything needed to reproduce an environment. For the code, we still recommend you use GitHub. Duplicated Studios will automatically bring the GitHub repo but remove all credentials or rights to commit. So, the person duplicating the Studio must have the ability to work on that GitHub repo.

