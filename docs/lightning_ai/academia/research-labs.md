# Research labs[](#research-labs)

Lightning Studios are ideal for research projects as they enable you to create and share reproducible environments, collaborate in real time, and manage the costs of each research project.

If you are running a research lab, we recommend creating a new organization and inviting all your lab members—for example, "LLM Lab".

# First time set up[](#first-time-set-up)

It takes <10 minutes to set up a new organization and invite all team members.

## Create an organization[](#create-an-organization)

There is no cost to create a new organization.

Create an organization with the name of the lab. Navigate to the top left of the screen and click the title on the top left. Then, click "New Organization":

https://pl-bolts-doc-images.s3.us-east-2.amazonaws.com/Docs\_Studios\_MP4/TeamManagement\_Academia\_UniversityLab\_CreateAnOrganization2.mp4

## Add organization admins[](#add-organization-admins)

Invite the members who will manage the organization. These are the PIs for the lab usually. Organization admins have elevated permissions to manage members, cloud accounts, budgets and more.

https://pl-bolts-doc-images.s3.us-east-2.amazonaws.com/Docs\_Studios\_MP4/TeamManagement\_Academia\_UniversityLab\_AddOrgAdmins2.mp4

Add admin to your Lab teamspace.

## Add organization members[](#add-organization-members)

Invite all lab members to the organization \(as members\). Each member automatically gets their own teamspace.

https://pl-bolts-doc-images.s3.us-east-2.amazonaws.com/Docs\_Studios\_MP4/TeamManagement\_Academia\_UniversityLab\_AddOrgMembers2.mp4

Add additional team members to the teamspace.

## Add cloud account \(optional\) [](#add-cloud-account-optionalandnbsp)

Your organization comes with the default, secure cloud account. Connect a private cloud account to use AWS credits \(like grant money, or academic credits.

https://pl-bolts-doc-images.s3.us-east-2.amazonaws.com/Docs\_Studios\_MP4/TeamManagement\_Academia\_UniversityLab\_AddCloudAccount.mp4

Connect a private cloud account.

Private cloud accounts consume cloud credits and run on your own private cloud infrastructure. If you work with sensitive data or need extra security, we recommend this method.

## Unlock more features[](#unlock-more-features)

It's free to get started with Lightning organizations. Pay as you go while you prototype and get projects started. As projects mature or you need advanced functionality, unlock new features by upgrading to different tiers. Compare [advanced features here](https://lightning.ai/pricing#compare) .

https://pl-bolts-doc-images.s3.us-east-2.amazonaws.com/TeamManagement\_Academia\_UniversityLab\_AddOrgAdmins2.mp4

Creating an organization is free. Upgrade to fit your needs.

If you have any questions, contact us directly or [write to us on our Discord](https://discord.gg/45NWVrFxMk) .

# Advantages[](#advantages)

Setting up a research lab on Lightning offers many advantages.

## Manage research budgets[](#manage-research-budgets)

Organize a research project in a teamspace to set a budget. Teamspace members will not be able to exceed that budget. Principal investigators can also set spending alerts and require permissions for activity that might exceed a threshold.

https://pl-bolts-doc-images.s3.us-east-2.amazonaws.com/Docs\_Studios\_MP4/TeamManagement\_Academia\_UniversityLab\_ManageResearchBudgets.mp4

Set a budget for your teamspace.

## Track spend[](#track-spend)

Each teamspace tracks the credit activity of all members and actions in the teamspace.

https://pl-bolts-doc-images.s3.us-east-2.amazonaws.com/TeamManagement\_Academia\_UniversityLab\_TrackSpend\_Teamspace2.mp4

Track activity within the teamspace.

Organization admins can also view the aggregate activity at the organization level for more granular control.

https://pl-bolts-doc-images.s3.us-east-2.amazonaws.com/Docs\_Studios\_MP4/TeamManagement\_Academia\_UniversityLab\_TrackSpend\_Org.mp4

Organization admins can view activity across teamspaces.

## Allocate compute resources[](#allocate-compute-resources)

Organizations have different grants, budgets, or compute available to certain research projects. Each teamspace has the ability to add a custom cloud compute resource.


Each teamspace can have a unique custom compute resource.

Select an Image

## Enable external collaboration[](#enable-external-collaboration)

Lightning allows members of different organizations to collaborate in the same teamspaces while respecting the security considerations of each individual organization. External contributors can join teamspaces on a per-project basis as "guests" who have access only to that teamspace.


External contributors can join individual teamspaces in an org as "guests."

Select an Image

## Full reproducibility[](#full-reproducibility)

Reproducibility in computational research has been nearly impossible until now. Publish Studios publicly or inside the lab that can be duplicated in a few minutes. Duplicate a published Studio to get an exact replica of the environment down to the installed packages, environment variables, files, and more.

https://pl-bolts-doc-images.s3.us-east-2.amazonaws.com/TeamManagement\_Academia\_UniversityLab\_FullReproducibility2.mp4

Duplicate a published Studio to get an exact replica of the environment, including all dependencies.

This allows work to be instantly open sourced in a way that can be fully replicated.

## Live collaboration[](#live-collaboration)

Researchers can collaborate with each other on the Studio to explore results, visualize experiments, share files/artifacts, and debug code and environments together. No need to set up local environments or figure out how to get a collaborator to reproduce your results.

https://pl-bolts-doc-images.s3.us-east-2.amazonaws.com/Docs\_Studios\_MP4/TeamManagement\_Academia\_UniversityLab\_LiveCollaboration.mp4

Use live sessions for real-time collaboration on research.

## Use cloud credits[](#use-cloud-credits)

The majority of research grants given by cloud providers go unused. Connect a cloud account in < 5 minutes to immediately start using those cloud credits. Cost saving features like auto-sleep, alerts and more, help users make their cloud credits last much longer on Lightning.


Lightning helps you make the most of every cloud credit.

Select an Image

## Open source work[](#open-source-work)

Work done on Studios can be open sourced and made public instantly. No need to "clean up" the code, or spend time writing lengthy instructions on how to reproduce the environment and "hope" users can replicate the exact same code and results the research presented. At the end of research, publish a Studio which can be accessible to anyone on the internet, or internally in your organization.

https://pl-bolts-doc-images.s3.us-east-2.amazonaws.com/Docs\_Studios\_MP4/TeamManagement\_Academia\_UniversityLab\_OpenSourceWork2.mp4

Publish your Studios to the public to contribute your work to the open source community.

# Organize work[](#organize-work)

Use these recommendations to structure work inside an organization.

## One teamspace per project[](#one-teamspace-per-project)

Set up a teamspace per research initiative \(this typically results in a publication\). This is normally done by organization members as new projects come up.

https://pl-bolts-doc-images.s3.us-east-2.amazonaws.com/Docs\_Studios\_MP4/TeamManagement\_Academia\_UniversityLab\_OneTeamspacePerProject2.mp4

Create one teamspace for each research initiative.

A teamspace isolates data access to a group of people under a shared goal. Each teamspace will group Studios and data related to the project. It also allows PIs to set cloud budgets. For example if the project is to create a cancer detection model , the teamspace will be "cancer detection" and the Studios in the teamspace will be different tasks \(train model, finetune, deploy, etc...\).


A teamspace with Studios that cover unique tasks in cancer detection.

Select an Image

## One Studio per task[](#one-studio-per-task)

Organization members will create multiple studios inside a teamspace. Each Studio should be isolated to one task with a stand-alone cloud environment.


Each Studio should address one task.

Select an Image

All studios can access the same files in the teamspace, so you can create a dataset on one Studio and access it from a second Studio.

https://pl-bolts-doc-images.s3.us-east-2.amazonaws.com/Docs\_Studios\_MP4/TeamManagement\_Academia\_UniversityLab\_OneStudioPerTask.mp4

All studios can access the same files within a teamspace.

## Create Studio templates[](#create-studio-templates)

A way to share work across the organization is to publish Studios to the internal library. Organization members can duplicate these Studios into different teamspaces.

https://pl-bolts-doc-images.s3.us-east-2.amazonaws.com/Docs\_Studios\_MP4/TeamManagement\_Academia\_UniversityLab\_CreateStudioTemplate2.mp4

Publish studios to the internal Studio templates gallery to share work across the organization.

