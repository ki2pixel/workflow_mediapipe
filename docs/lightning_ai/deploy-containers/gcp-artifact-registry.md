# GCP artifact registry[](#gcp-artifact-registry)

Start a deployment from a private Docker image stored on a private [GCP Artifact Registry](https://cloud.google.com/artifact-registry/docs/overview) . This feature is available when you attach your own GCP account to Lightning AI.

## Enable GCP role[](#enable-gcp-role)

First step is to the give Lightning permission to pull images using the project role we created to attach your GCP account to Lightning.

1\. Find the project role that we created for your BYOC account. They are named "Lightning AI BYOC Project Role \(<your account name>\), permissions should look like:


Lightning project roles

Select an Image

2\. Edit the role to allow it to access your GCP Artifact registry:


Filtering the roles

Select an Image

3\. Select all permissions to enable pulling images \(it needs to list, download, etc.\)


enabling registry permissions

Select an Image

4\. Now, filter by "artifactregistry.repositories" \(you can remove the create/delete permissions\):


Add the registry repositories get/list/download permissions

Select an Image

5\. Save the role.

## Deploy[](#deploy)

Choose the private image name and tag when starting the deployment.


Select an Image

