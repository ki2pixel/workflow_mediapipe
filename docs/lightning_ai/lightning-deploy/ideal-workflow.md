# Ideal workflow[](#ideal-workflow)

Lightning offers 3 ways of starting dedicated deployments. The three options give you a trade-off between ease and speed.

Traditional deployment workflows were built for web apps - not AI. They rely on containers, YAML files, and fragile handoffs between teams. AI developers just want to ship models, not manage Dockerfiles and Kubernetes clusters.

## Option A: Live serving[](#option-a-live-serving)

Live serving allows you to debug and develop cloud servers like they're running on your laptop.

Debugging cloud deployments is slow and disconnected from development. Live Serving gives you a localhost-like loop in the cloud, so you can test with real traffic, iterate instantly, and move from prototype to production without context switching or redeploy pain.

With Live Serving, you start your server inside a cloud Studio, send it real traffic, and debug it live. You get the convenience of ` ` localhost` ` , but in the same environment it will eventually run in production.

https://pl-bolts-doc-images.s3.us-east-2.amazonaws.com/app-2/deploy\_local.mp4

* *How it works: **

  - Start a Studio \(CPU or GPU\)

  - Open VS Code or Jupyter in the Studio

  - Run your server code \( ` fastapi ` , ` vllm ` , ` LitServe ` , etc.\) like you would locally

  - Test endpoints interactively from inside the Studio


* *Upgrade to internet traffic: **

https://pl-bolts-doc-images.s3.us-east-2.amazonaws.com/app-2/internet\_traffic\_deploy.mp4

To receive real API traffic \(e.g. from Discord or Slack\):

  - Install the API plugin

  - Expose the server’s port to the internet

  - Your server is now live, persistent, and internet-accessible


This is ideal for prototyping, debugging, or even running a lightweight 24/7 service without full infra setup.

## Option B: Snapshot deploy[](#option-b-snapshot-deploy)

Turn your Studio into a production-grade server - no Docker, no YAML.

Manually packaging servers into containers slows down iteration and forces AI builders to learn DevOps. Snapshot Deploy eliminates that overhead by turning your working Studio into a real deployment - no Docker, no YAML, just one click to production.

Once your live server is working, you can instantly turn it into a production deployment. Lightning snapshots the full Studio environment \(code, packages, ports, everything\) and launches it as a scalable, monitored deployment.

https://pl-bolts-doc-images.s3.us-east-2.amazonaws.com/app-2/studio\_deploy.mp4

* *How it works: **

  - Install the Deployment plugin in the Studio

  - Click “New Deployment”, select “Studio” as source

  - Type the same command you'd use to run the server

  - Click Deploy


* *Lightning handles: **

  - Packaging the environment

  - Launching a deployment

  - Monitoring traffic, autoscaling, logging, and cold starts


✅ Snapshot deployments are the fastest way to go from dev to prod without touching infra.

## Option C: Container deploy[](#option-c-container-deploy)

Reduce cold starts, ensure portability, and scale like an infra team.

Snapshot deploys are great for speed, but if you need faster cold starts or precise control over dependencies, move to containers. You can use your own container registry or Lightning’s.

https://pl-bolts-doc-images.s3.us-east-2.amazonaws.com/app-2/container-deploy-demo.mp4

* *To deploy a container: **

  1. Build the container

  2. Push it to Lightning’s container registry \(or [DockerHub](https://lightning.ai/docs/overview/deploy/dockerhub) , [GCP artifact registry](https://lightning.ai/docs/overview/deploy/gcp-artifact-registry) , [AWS ECR](https://lightning.ai/docs/overview/deploy/aws-ecr) , or [GitHub containers](https://lightning.ai/docs/overview/deploy/github-containers) \)

  3. Click Deploy in the Containers tab of the teamspace


* *Example: deploy a vLLM container. **

Here is a vLLM Dockerfile.

`1 2 3 4 5 6 7 8 9 10 11 ` ` FROM python:3.10-slim # Install vLLM RUN pip install --upgrade pip && \ pip install vllm # Expose the vLLM default port EXPOSE 8000 # Start the vLLM server with a Hugging Face model CMD ["python", "-m", "vllm.entrypoints.api_server", "--model", "meta-llama/Llama-2-7b-chat-hf"]`

Push the container

Login to registry

Login to the Lightning container registry

Get the container

Build the vLLM container using the Dockerfile

Tag

Tag the container

Push

Push to the Lightning container registry

`1 2 3 4 5 6 7 8 9 10 11 ` ` # login export LIGHTNING_API_KEY=XXXXXXXXX-XXXXXXXXXXXXXXXXXX-XXXXXXXXXXXXXXXXXXX echo $LIGHTNING_API_KEY | docker login litcr.io --username=your-lightning-username --password-stdin  docker build -t my-vllm-server . # tag docker tag my-vllm-server:latest litcr.io/lit-container/org-or-user-name/teamspace-name/my-vllm-server  # push docker push litcr.io/lit-container/org-or-user-name/teamspace-name/my-vllm-server  `

Then visit the "containers" tab in the teamspace, select the container and click "deploy" on the top right.

🚀 You can also build and push containers directly from a Studio with:

`1 ` ` lightning upload container my-vllm-server --teamspace org-or-user-name/teamspace-name --tag latest`

# LitServe - simplest model serving[](#litserve-simplest-model-serving)

Most AI inference tools are built around single-model APIs with rigid abstractions. They lock you into serving one model per server, with no way to customize internals like batching, caching, or kernels. This makes it hard to build full systems like RAG or agents without stitching together multiple services. The result is complex MLOps orchestration, slower iteration, and bloated infrastructure.

* *LitServe flips this paradigm: ** Write full AI pipelines, not just models, in clean, extensible Python. Built on FastAPI but optimized for AI workloads, LitServe supports multi-model serving, streaming, batching, and custom logic - all from a single server. Deploy in one click with autoscaling, monitoring, and zero infrastructure overhead. Or run it self-hosted with full control and no lock-in.

Here's a toy example to illustrate a multi-model server with LitServe

`1 2 3 4 5 6 7 8 9 10 11 12 13 14 15 16 17 18 19 20 21 22 23 24 25 26 27 ` ` import litserve as ls # define the api to include any number of models, dbs, etc... class SimpleLitAPI(ls.LitAPI): def setup(self, device): self.model1 = lambda x: x * *2 self.model2 = lambda x: x * *3 def decode_request(self, request): # get inputs to /predict return request["input"] def predict(self, x): # perform calculations using both models a = self.model1(x) b = self.model2(x) c = a + b return {"output": c} def encode_response(self, output): # package outputs from /predict return {"output": output} if * *name ** == " * *main * *": # 12+ features like batching, streaming, etc... server = ls.LitServer(SimpleLitAPI(max_batch_size=1), accelerator="auto") server.run(port=8000)`

If you’re using LitServe, deploying a model is as simple as:

`1 ` ` lightning deploy server.py --cloud`

LitServe handles:

  - Batching

  - Streaming

  - Device selection

  - Endpoint creation


It works with any model, from LLMs to diffusion to classical models.

# Beyond one model[](#beyond-one-model)

Don’t stitch together tools for agents, RAG stacks, or model routing. Lightning natively supports [multi-model deployments](https://lightning.ai/docs/overview/deploy/multi-model-systems) through its Pipelines feature. Define chains of jobs, servers, and microservices - each autoscaling independently - without Kubernetes.

