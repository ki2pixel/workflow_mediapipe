# GitHub containers[](#github-containers)

To use private images from [GitHub Container registry](https://docs.github.com/en/packages/working-with-a-github-packages-registry/working-with-the-container-registry) you will need to create a personal access token.

## Create personal token[](#create-personal-token)

1\. Go to your [personal access tokens \(classic\)](https://github.com/settings/tokens) page

2\. Click on "Generate new token \(classic\)" button. It has to be "classic" token as GitHub packages do not support fine-grained.

3\. Select "read:packages":


read:packages permission is needed

Select an Image

## Deploy[](#deploy)

When creating the deployment, click on registry credentials, in the username specify your GitHub username \(they have to match\) and the personal access token as the password.

Click "Deploy"


specify registry credentials next to your private image

Select an Image

