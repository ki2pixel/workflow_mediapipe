# Submit jobs[](#submit-jobs)

You can submit jobs via the web UI or SDK. A job can run using either a Studio environment or a Docker image as its environment.


# Use a Studio environment[](#use-a-studio-environment)

A Studio environment contains everything your code needs to execute, including code, data, dependencies, and environment variables. When you submit a job using the Studio, the environment is forked at submission, allowing you to continue editing without affecting the submitted job.

https://pl-bolts-doc-images.s3.us-east-2.amazonaws.com/Docs\_Studios\_MP4/Docs\_Studios\_Jobs\_Animation3.mp4

Jobs are non-interactive, parallel executions of your Studio.

## Submit via the web UI[](#submit-via-the-web-ui)

  1. Click the Jobs icon in the Studio.

  2. Select the file to execute.

  3. Hit Submit


https://pl-bolts-doc-images.s3.us-east-2.amazonaws.com/Docs\_Studios\_MP4/Docs\_Studios\_Jobs\_Submit.mp4

How to submit a job

## Submit via code \(SDK\)[](#submit-via-code-sdk)

Use the Lightning SDK to submit a job programmatically:

`1 2 3 4 5 6 7 8 ` ` from lightning_sdk import Studio, Machine, Job studio = Studio(name='my-studio', teamspace='my-teamspace', user='my-user') # Define the command to run and submit the job submitted_job = Job.run(command="echo Hello, Lightning!", name="echo-example", machine=Machine.CPU, studio=studio) print(f"Job submitted: {submitted_job}")`

## Submit via terminal \(CLI\)[](#submit-via-terminal-cli)

After installing the latest version of the command line interface \(CLI; ` pip install --upgrade lightning-sdk ` \), submit a job by running

`1 2 3 4 5 ` ` lightning run job \ --command="python train.py" \ --studio=my-studio \ --teamspace=my-teamspace \ --org=my-org`

For additional information on submitting a job from the CLI, run

`1 ` ` lightning run job --help`

# Use a Docker image[](#use-a-docker-image)

A Docker image can be used as the job environment, providing a fully isolated and consistent setup.

## Submit via code \(SDK\)[](#submit-via-code-sdk)

Submit a job with a Docker image:

`1 2 3 4 5 6 7 8 9 10 11 12 13 ` ` from lightning_sdk import Job, Teamspace, Machine teamspace = Teamspace(name="my-teamspace", user="my-user") submitted_job = Job.run( name="my-job", command="python /scripts/train.py", image="litcr.io/lit-container/<my_lightning_org>/<my_teamspace>/<my_image>:<tag>", machine=Machine.L40s, teamspace=teamspace ) print(submitted_job.status)`

## Private DockerHub image[](#private-dockerhub-image)

For private images, add your credentials as a [secret](https://lightning.ai/docs/overview/Studios/secrets?settings=secrets) :

For accessing, private images on DockerHub, make sure to add your credentials as a [secret](https://lightning.ai/docs/overview/Studios/secrets?settings=secrets) to your account. These will then automatically be used to pull your specified image. On the SDK, these can then be specified as

`1 2 3 4 5 6 7 8 9 10 11 12 13 14 ` ` from lightning_sdk import Job, Teamspace, Machine, Status # Get the teamspace you want to submit your Job in teamspace = Teamspace(name="my-teamspace", user="my-user") # Submit the Job submitted_job = Job.run( name="my-job", command="python /scripts/train.py", image="my-image", machine=Machine.L40s, teamspace=teamspace, image_credentials="my-secret-name" )`

with ` "my-secret-name" ` being whatever you specified as the name of your credential secret.

## Private image with AWS ECR[](#private-image-with-aws-ecr)

To use private ECR images, [add a private cloud account](https://lightning.ai/docs/team-management/organizations/manage-organization-clusters) first. Once that's done, use the cloud account to authenticate to ECR:

`1 2 3 4 5 6 7 8 9 10 11 12 13 14 ` ` from lightning_sdk import Job, Teamspace, Machine, Status # Get the teamspace you want to submit your Job in teamspace = Teamspace(name="my-teamspace", user="my-user") # Submit the Job submitted_job = Job.run( name="my-job", command="python /scripts/train.py", image="my-image", machine=Machine.L40s, teamspace=teamspace, cloud_account_auth=True )`

## Submit via terminal \(CLI\)[](#submit-via-terminal-cli)

After installing the latest version of the command line interface \(CLI; ` pip install --upgrade lightning-sdk ` \), submit a job by running

`1 2 3 4 5 ` ` lightning run job \ --image="my-image:latest" \ --command="python /train.py" \ --teamspace=my-teamspace \ --org=my-org`

