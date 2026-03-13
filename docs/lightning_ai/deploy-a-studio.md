# Deploy a Studio[](#deploy-a-studio)

Turn your Studio into a production-grade server - no Docker, no YAML.

Manually packaging servers into containers slows down iteration and forces AI builders to learn DevOps. Snapshot Deploy eliminates that overhead by turning your working Studio into a real deployment - no Docker, no YAML, just one click to production.

Once your live server is working, you can instantly turn it into a production deployment. Lightning snapshots the full Studio environment \(code, packages, ports, everything\) and launches it as a scalable, monitored deployment.

# Deploy via the UI[](#deploy-via-the-ui)

## Initial Deployment[](#initial-deployment)

https://pl-bolts-doc-images.s3.us-east-2.amazonaws.com/app-2/studio\_deploy.mp4

Create a deployment from the Studio snapshot with ease

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

## Iterative re-deploy[](#iterative-re-deploy)

Once your deployment is live and working, you can simply go back to your Studio and start working on the next version of your API. Once ready to re-deploy, simply update the deployment.

https://pl-bolts-doc-images.s3.us-east-2.amazonaws.com/Docs\_Studios\_MP4/Deploy-StudioSnapshot-Deployiterative.mp4

Update the deployment to the latest Studio version

* *How it works: **

  - Click on the Deployment Plugin and select the deployment you have already created

  - Click "Update" Button on the top right.

  - After reviewing the settings, click "Update" to validate the re-deployment


* *Lightning handles: **

  - Packaging a new version of the Studio environment

  - Re-deploying the deployment gracefully using a rollout strategy

  - Automatic revert if something goes wrong.


## Revert versions[](#revert-versions)

If you want to restore a previous version, simply find the release you want and restore it.

https://pl-flash-data.s3.us-east-1.amazonaws.com/restore-any-releases.mp4

Restore an earlier release of the deployment

* *How it works: **

  - Click on the Deployment Plugin and select the deployment you have already created

  - Click "Releases" tab

  - Click on the 3 dots at the beginning of the release you want to restore

  - Confirm the restoration of the previous release


* *Lightning handles: **

  - Keep the snapshot history

  - Efficient and gracefully handles rollout


# Via the SDK[](#via-the-sdk)

## Single server[](#single-server)

By running this code within a Studio, it takes the current enviroment of the Studio and run it as a deployment

`1 2 3 4 5 6 7 8 9 10 11 12 13 ` ` from lightning_sdk import Studio, Deployment from lightning_sdk.deployment import HttpHealthCheck deployment = Deployment() deployment.start( studio=Studio(), command="python -m http.server", ports=[8000], health_check=HttpHealthCheck( path="/", port=8000 ) )`

In this other example, this code defines a FastAPI server with basic endpoints and orchestrates its deployment using the Lightning SDK's ` Studio ` and ` Deployment ` classes. It automates setting up a development environment, uploads the server code, and validates the deployment by sending a test request to ensure it returns the expected response.

Step 1

Imports

Step 2

Define the server code

Step 3

Create a new Studio

Step 4

Install FastAPI

Step 5

Upload the server.py file to the newly created Studio

Step 6

Create a Deployment from the Studio

Step 7

Send a request to the Deployment

`1 2 3 4 5 6 7 8 9 10 11 12 13 14 15 16 17 18 19 20 21 22 23 24 25 26 27 28 29 30 31 32 33 34 35 36 37 38 ` ` from lightning_sdk import Studio, Deployment from lightning_sdk.deployment import HttpHealthCheck from datetime import datetime  server_code = """ from fastapi import FastAPI  app = FastAPI()  @app.get("/") def read_root():  return {"Hello": "World"} """ studio_name = "studio-" + datetime.now().strftime("%m-%d_%H:%M:%S") studio = Studio(studio_name) studio.start() studio.run_with_exit_code("pip install 'fastapi[standard]'") with open("server.py", "w") as f: f.write(server_code) studio.upload_file("server.py") # Create a Deployment from that Studio deployment = Deployment() deployment.start( studio=studio, command="fastapi run server.py", ports=[8000], health_check=HttpHealthCheck( path="/", port=8000 ) ) resp = deployment.get("/") assert resp.json() == {"Hello": "World"}`

## Multiple servers[](#multiple-servers)

This code utilizes the Lightning SDK to launch multiple Python server scripts, ` server_1.py ` and ` server_2.py ` , concurrently within a specified development environment labeled "your-studio-name". It sets up a deployment that makes both servers accessible on ports 3000 and 3001, respectively.

`1 2 3 4 5 6 7 8 9 10 11 12 13 ` ` from lightning_sdk import Studio, Deployment commands = [ "python server_1.py --port 3000 &", "python server_2.py --port 3001 &", ] deployment = Deployment() deployment.start( studio=Studio("your-studio-name"), commands=commands, ports=[3000, 3001], )`

## Update Secrets[](#update-secrets)

This code updates an existing deployment by adding a secret and an environment variable using the ` Deployment ` class from the ` lightning_sdk ` . The ` update ` method adds a secret named ` "my-secret" ` and an environment variable ` "env-name" ` with the value ` "env-value" ` to the specified deployment configuration.

`1 2 3 4 ` ` from lightning_sdk.deployment import Deployment, Secret, Env deployment = Deployment("existing-deployment") deployment.update(env=[Secret(name="my-secret"), Env(name="env-name", value="env-value")])`

This code snippet updates the environment configuration of a target deployment using the environment variables from a source deployment. It initializes two deployment instances \( ` source_deployment ` and ` target_deployment ` \) and then copies the environment configuration \( ` env ` \) from the ` source_deployment ` to the ` target_deployment ` using the ` update ` method.

`1 2 3 4 5 6 ` ` from lightning_sdk.deployment import Deployment, Secret, Env source_deployment = Deployment("source-existing-deployment") target_deployment = Deployment("target-existing-deployment") target_deployment.update(env=source_deployment.env)`

