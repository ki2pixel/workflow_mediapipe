# Duplicate Studios[](#duplicate-studios)

Duplicate Studios to reproduce work 100%. This comes up when others need a copy of something you are working on. However, today it requires many steps like sharing a GitHub project, Docker images, and more. Then the person looking to replicate the work spends weeks trying to get it to work and it's not exactly the same.

Duplication in Studios solves this problem by letting users copy everything in a Studio, including the environment, files, packages, dependencies, data, and more. Try it out by duplicating any [community Studio](https://lightning.ai/studios) .

## Duplicate within a teamspace[](#duplicate-within-a-teamspace)

To duplicate a Studio in a Teamspace, simply press the "duplicate" button:

https://pl-bolts-doc-images.s3.us-east-2.amazonaws.com/Docs\_Studios\_MP4/Docs\_DevelopmentWorkflow\_DuplicateStudiosinTeamspace.mp4

How to duplicate studios

The wait time corresponds to the size of a Studio. If a Studio has a few hundred GBs of files, it might take a few minutes. Otherwise, expect duplication to happen in <1 minute.

If you are collaborating on code, you should still use your code manager like git inside the Studio like you normally do.


Use any code manager, like git, in your Studio

Select an Image

## Duplicate across teamspaces[](#duplicate-across-teamspaces)

A Studio can also be duplicated to another teamspace. Simply find the Studio you want to duplicate, click the duplicate button and select the teamspace.

https://pl-bolts-doc-images.s3.us-east-2.amazonaws.com/Docs\_Studios\_MP4/Docs\_DevelopmentWorkflow\_DuplicateStudios\_TeamspacetoTeamspace.mp4

Duplicating a Studio from one teamspace to another.

## Duplicate by publishing[](#duplicate-by-publishing)

Another method of enabling duplication is to publish the Studio. Publish to the community Studios or to your organization's private library of Studios.

https://pl-bolts-doc-images.s3.us-east-2.amazonaws.com/Docs\_Studios\_MP4/Docs\_Studios\_DuplicateStudios\_DuplicateByPublishing2.mp4

Publish to your organization's studio template gallery

Anyone with access to the Studio will be able to duplicate it. For example, if you publish inside Acme corp's organization, only Acme members will be able to duplicate the Studios.

## Duplicate across cloud accounts[](#duplicate-across-cloud-accounts)

We currently do not support duplicating across cloud accounts. Please get in touch if you need this ability.

## Credentials and sensitive information[](#credentials-and-sensitive-information)

Studio duplicates will not include SSH files, AWS credentials, Docker credentials, or the shell history.

If you need to use any additional credentials with your Studio, add them in the ` .lightning_studio/.studiorc ` file:

`1 ` ` export PERSONAL_TOKEN="0000-0000-0000-0000"`

