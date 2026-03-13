# Lit container registry[](#lit-container-registry)

Centralize, store, manage and deploy Docker containers. With Lightning container registry gone are the days of having to manage and configure your own Docker registry. Instead allow Lightning AI to do the manual labor for you freeing up time for you to spend on model development.

https://pl-bolts-doc-images.s3.us-east-2.amazonaws.com/app-2/container-deploy-demo.mp4

# Benefits[](#benefits)

✅ * *One platform: ** Enhanced interoperability between all Lightning products you use on a daily basis such as Lightning deploy.

✅ * *Instantly scale: ** Containers stored on Lightning can be deployed and scaled with a few clicks of a button.

✅ ** Ready when you are: * *The second you navigate to the containers page you will be able to push containers to container registry.

✅ * *Security, by default: ** All containers are stored encrypted at rest with AES-256 encryption.

✅ * *Data privacy when needed: ** With BYOC, all containers are stored in private AWS S3 storage. Push, deploy and scale all within your VPC, no AWS certifications needed.
_Note: only AWS is supported for now._

# Upload via Lightning CLI[](#upload-via-lightning-cli)

First, install the Lightning CLI

`1 ` ` pip install -U lightning-sdk`

## From Studio[](#from-studio)

Build and push containers from Studio. Once pushed, hit Deploy\!

https://pl-bolts-doc-images.s3.us-east-2.amazonaws.com/deploy\_workflow.mp4

To illustrate, let's build and push the vLLM container. First define the Dockerfile

`1 2 3 4 5 6 7 8 9 10 11 ` ` FROM python:3.10-slim # Install vLLM RUN pip install --upgrade pip && \ pip install vllm # Expose the vLLM default port EXPOSE 8000 # Start the vLLM server with a Hugging Face model CMD ["python", "-m", "vllm.entrypoints.api_server", "--model", "meta-llama/Llama-2-7b-chat-hf"]`

Build and push the container

Build

Build the container on the Studio

Push

Push to Lightning container registry

`1 2 3 4 5 ` ` # build docker build -t my-vllm-server . # push lightning upload container my-vllm-server --teamspace org-or-user-name/teamspace-name --tag latest`

## From Mac[](#from-mac)

To push from the Mac, install and start Docker:

Install

Install Docker if it's not already installed

Upload

Upload the vLLM container built earlier to the organization or username and teamspace

`1 2 3 4 5 6 7 8 9 ` ` # install brew install docker  [Run Docker] Make sure Docker is running # start open -a Docker  # upload lightning upload container my-vllm-server --teamspace org-or-user-name/teamspace-name --tag latest`

## From Linux[](#from-linux)

To push a container from Linux, install and start Docker and push

Install Docker

Setup Docker

Start Docker

Make sure Docker is running

Upload

Upload the container \(same vLLM container as above\) to Lightning registry

`1 2 3 4 5 6 7 8 ` ` # install curl -fsSL https://get.docker.com | bash  # start sudo systemctl restart docker  # upload lightning upload container my-vllm-server --teamspace org-or-user-name/teamspace-name --tag latest`

## From Windows[](#from-windows)

To push a container from Windows, [first install Docker](https://docs.docker.com/desktop/setup/install/windows-install/) . Once it's installed, push the container.

`1 ` ` lightning upload container my-vllm-server --teamspace org-or-user-name/teamspace-name --tag latest`

# Deploy container[](#deploy-container)

Containers stored on Lightning's native registry can be deployed in one-click. Upload the container, select the container and click "Deploy".


https://pl-bolts-doc-images.s3.us-east-2.amazonaws.com/app-2/container-deploy-demo.mp4

# Upload via Docker CLI[](#upload-via-docker-cli)

For those used to working with Docker, Lightning supports direct Docker CLI uploads.

First, login to the Lightning container registry \( [get your keys here](https://lightning.ai/lightning-ai/home?settings=keys) \), tag the container and push.

Login to registry

Login to the Lightning container registry

Get the container

Build the vLLM container using the Dockerfile

Tag

Tag the container

Push

Push to the Lightning container registry

`1 2 3 4 5 6 7 8 9 10 11 ` ` # login export LIGHTNING_API_KEY=XXXXXXXXX-XXXXXXXXXXXXXXXXXX-XXXXXXXXXXXXXXXXXXX echo $LIGHTNING_API_KEY | docker login litcr.io --username=your-lightning-username --password-stdin  docker build -t my-vllm-server . # tag docker tag my-vllm-server:latest litcr.io/lit-container/org-or-user-name/teamspace-name/my-vllm-server  # push docker push litcr.io/lit-container/org-or-user-name/teamspace-name/my-vllm-server  `

