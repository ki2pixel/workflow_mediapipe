# GitHub and GitLab[](#github-and-gitlab)

Studios are not meant to manage code versioning. For that, we recommend you use either GitHub or GitLab.


Code is just one part within a Studio

Select an Image

## GitHub integration[](#github-integration)

You can integrate GitHub during onboarding.

https://pl-bolts-doc-images.s3.us-east-2.amazonaws.com/Docs\_Studios\_MP4/Docs\_Studios\_GitHub\_GitHubIntegration.mp4

If you integrated your GitHub during onboarding, you can use git as is

If you want to integrate GitHub after onboarding, go to * *Global settings > Integrations > Add Git Integrations > Github * *. Note: Github credentials are on a per-user basis. You can not set up a Github account for an entire organization or a teamspace.

https://pl-bolts-doc-images.s3.us-east-2.amazonaws.com/Docs\_Studios\_MP4/Docs\_Studios\_GitHub\_GitHubIntegration\_GlobalAuthorization.mp4

How to integrate GitHub if you didn't during onboarding

## GitLab integration[](#gitlab-integration)

You can also integrate GitLab during onboarding. If you've already completed onboarding, but want to integrate GitLab, go to * *Global settings > Integrations > Add Git Integration > GitLab * *.

https://pl-bolts-doc-images.s3.us-east-2.amazonaws.com/Docs\_Studios\_MP4/GitLab.mp4

How to integrate GitLab if you didn't during onboarding

This will then ask you to put in your registry URL and your username, take you to GitLab to generate a personal access token which has to be pasted back in the integration setup dialog.

### Manual SSH keys[](#manual-ssh-keys)

In case you want to integrate manually with SSH keys instead of the integration, you can do the following steps:

  1. Generate an SSH Key Pair

    1. In a Studio terminal, run ` ssh-keygen`

    2. Click enter to accept the default file location

    3. Create a passphrase

  2. Copy the public key to GitLab

    1. ` cat ~/.ssh/id_rsa.pub`

    2. copy and paste it into your user settings at ` User Settings --> SSH Keys --> Add new key`

  3. Edit ` ~/.lightning_studio/.studiorc ` file in your Studio

    1. Add a line with ` GITLAB_SSH_KEY="<Private_Key_With_Header_And_Footer>"`

    2. add a second line with ` eval ` ssh-agent -s ` > /dev/null && echo $GITLAB_SSH_KEY | ssh-add -`

  4. Restart terminal and clone your repository

    1. After opening a new terminal you can run ` git clone git@gitlab.com:your-username/your_repository.git`


This ensures you will be authenticated to use your GitLab repo in each new Studio you create under your current user id.

https://pl-bolts-doc-images.s3.us-east-2.amazonaws.com/Docs\_Studios\_MP4/Overview\_Studios\_GitHub\_and\_Gitlab.mp4

Securely connect to GitLab and clone your repo

