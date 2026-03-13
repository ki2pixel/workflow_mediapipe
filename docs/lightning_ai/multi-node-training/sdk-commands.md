# SDK commands[](#sdk-commands)

The MMT class in the Lightning SDK allows you to run multi-machine jobs asynchronously inside a Studio. Use this to offload tasks like data processing, training runs, or inference jobs that do not require interactive execution but multiple nodes communicating with each other.

The SDK is automatically available inside Studios. To use the SDK outside a Studio, install it with:

`1 ` ` pip install --upgrade lightning-sdk`

Ensure you authenticate using environment variables or login via CLI.

`1 2 ` ` export LIGHTNING_USER_ID=your-user-id export LIGHTNING_API_KEY=your-api-key`

# Submit a MMT[](#submit-a-mmt)

Here is a full example of how to submit a multi-machine job.

`1 2 3 4 5 6 7 8 9 10 11 12 13 14 15 16 17 18 19 20 21 22 23 24 25 ` ` # Install the Lightning SDK # pip install lightning-sdk # Export authentication variables # export LIGHTNING_USER_ID=your-user-id # export LIGHTNING_API_KEY=your-api-key from lightning_sdk import Studio, Machine, MMT # Step 1: Initialize a Studio studio = Studio(name="batch-processing", teamspace="my-teamspace", user="my-user") studio.start() # Step 3: Run a Multi-machine job job = MMT.run(command="python process_data.py", name="data-job", machine=Machine.CPU, studio=studio, num_machines=2) # Step 4: Monitor Job Status print(job.status) # Running, Completed, Failed # Step 5: Stop or Delete a Job # job.stop() # Gracefully stop a running job # job.delete() # Cancel and remove the job # Step 6: Shut Down the Studio studio.stop() `

## Initialize a Studio[](#initialize-a-studio)

Before running a job, first initialize and start a Studio:

`1 2 3 4 ` ` from lightning_sdk import Studio studio = Studio(name="batch-processing", teamspace="my-teamspace", user="my-user") studio.start()`

## Submit the Job[](#submit-the-job)

With the Studio defining the compute environment, submit the multi-machine job:

`1 2 ` ` job = MMT.run(command="python process_data.py", name="data-job", machine=Machine.CPU, studio=studio, num_machines=2)`

## List running multi-machine jobs[](#list-running-multi-machine-jobs)

`1 2 3 4 ` ` teamspace = Teamspace("my-teamspace", user="my-user") for job in teamspace.multi_machine_jobs: print(job.name, job.status) `

## Check multi-machine status[](#check-multi-machine-status)

`1 2 ` ` job = MMT("data-job", teamspace="my-teamspace", user="my-user") print(job.status) # Running, Completed, Failed `

## Stop or cancel a multi-machine job[](#stop-or-cancel-a-multi-machine-job)

If a job is no longer needed, you can stop or delete it:

`1 2 ` ` job.stop() # Gracefully stops a job job.delete() # Cancels and removes the job`

# Run multiple jobs in parallel[](#run-multiple-jobs-in-parallel)

You can launch multiple jobs on different machine types:

`1 2 3 ` ` MMT.run(command="python preprocess.py", name="preprocess", machine=Machine.CPU, studio=studio, num_machines=2) MMT.run(command="python train.py", name="train-job", machine=Machine.A10G, studio=studio, num_machines=2) MMT.run(command="python infer.py", name="inference", machine=Machine.L4, num_machines=2) `

# Automate Jobs[](#automate-jobs)

## GitHub actions[](#github-actions)

You can schedule jobs using GitHub Actions to run at a fixed time:

`1 2 3 4 5 6 7 8 9 10 11 12 13 14 15 16 17 18 19 20 21 22 23 24 25 26 27 28 29 ` ` name: Scheduled Job on: schedule: - cron: '0 3 * * *' # Runs at 3 AM UTC daily jobs: run_batch: runs-on: ubuntu-22.04 steps: - name: Set up Python uses: actions/setup-python@v2 with: python-version: "3.10" - name: Install Lightning SDK run: pip install lightning-sdk - name: Start a Job run: | python -c " \ from lightning_sdk import Studio, MMT, Machine; \ studio = Studio(name='batch-pipeline', teamspace='my-team', user='ci-bot'); \ studio.start(); \ MMT.run(command='python daily_task.py', name='daily-task', studio=studio, machine=Machine.A10, num_machines=2); \ studio.stop();" env: LIGHTNING_USER_ID: ${{ secrets.LIGHTNING_USER_ID }} LIGHTNING_API_KEY: ${{ secrets.LIGHTNING_API_KEY }} `

  - Use CPU machines for lightweight preprocessing tasks.

  - Use GPU machines for deep learning inference and training.

  - Enable interruptible mode for cost-saving on long-running multi-machine jobs.

  - Chain multi-machine jobs using status checks to create multi-step pipelines.


# API Reference[](#api-reference)

## \_\_init\_\_\(\)[](#init)

The \_\_init\_\_\(\) method fetches an existing multi-machine job and accepts the following arguments:

Add row above

Add row below

Delete row

Add column to left

Add column to right

Delete column

* *Parameter **

* *Type **

* *Description **

* *Default **

name

str

The name of the Job

-

teamspace

str | Teamspace

The teamspace the job is part of

None, Inferred from environment

org

str | Organization

The name of the organization owning the teamspace in case it is owned by an org

None, Inferred from environment

user

str | User

The name of the user owning the teamspace in case it is owned by a user instead of an org

None, Inferred from environment

* *Example: **

`1` ` job = MMT("data-job", teamspace="my-teamspace", user="my-user")`

## run\(\)[](#run)

The ` run() ` method submits a new multi-machine job and accepts the following arguments:

Add row above

Add row below

Delete row

Add column to left

Add column to right

Delete column

Parameter

Type

Description

Default

name

str

The name of the job

-

machine

Machine

Machine to run the Job on

-

num\_machines

int

The number of machines to run the job on

-

`command`

`str`

The command to run inside the Studio

None, The command to run inside your job. Required is using a Studio as compute environment. Optional for docker jobs. In case it's not specified for docker jobs, these will run the default command specified by the image.

studio

Studio | str | None

The studio env to run the job with. Mutually exclusive with image.

None, Inferred from environment in case image is not specified.

image

str | None

The docker image to run the job with. Mutually exclusive with studio.

None

teamspace

Teamspace | str | None

The teamspace the job should be associated with.

None, Inferred from the studio if used as compute environment, else inferred from environment.

org

str | Organization | None

The organization owning the teamspace \(if any\).

None, inferred from either Studio \(if used as compute environment\), teamspace \(if provided\) or environment.

user

str | User | None

The user owning the teamspace \(if any\).

None, inferred from either Studio \(if used as compute environment\), teamspace \(if provided\) or environment.

cloud\_account

str | None

The cloud acocunt to run the job on

None, inferred from the Studio \(if used as compute environment\) or environment if possible. Falls back to teamspace default cloud-account otherwise.

env

Dict\[str, str\] | None

Environment variables to set inside the job.

None

interruptible

bool

Whether the job should run on interruptible instances. They are cheaper but can be preempted.

False

image\_credentials

str | None

The credentials used to pull the image. Required if the image is private. This should be the name of the respective credentials secret created on the Lightning AI platform.

None

cloud\_account\_auth

bool

Whether to authenticate with the cloud account to pull the image. Required if the registry is part of a cloud provider \(e.g. ECR\).

False

entrypoint

str

The entrypoint of your docker container. To use the pre-defined entrypoint of the provided image, set this to an empty string. Only applicable when submitting docker jobs.

"sh -c", which just runs the provided command in a standard shell.

path\_mappings

Dict\[str, str\] | None

Dictionary of path mappings. The keys are the path inside the container whereas the value represents the data-connection name and the path inside that connection. Should be of form ` { "<CONTAINER_PATH_1>": "<CONNECTION_NAME_1>:<PATH_WITHIN_CONNECTION_1>", "<CONTAINER_PATH_2>": "<CONNECTION_NAME_2>"} ` If the path inside the connection is omitted it's assumed to be the root path of that connection.Only applicable when submitting docker jobs.

None

* *Example: **

`1` ` job = MMT.run(command="python process_data.py", name="data-job", machine=Machine.T4, num_machines=2, studio=studio) `

## stop\(\)[](#stop)

Stops the respective job. Accepts no arguments.

* *Example: **

`1 2` ` job = MMT("data-job", teamspace="my-teamspace", org="my-org") job.stop()`

## delete\(\)[](#delete)

Deletes the respective multi-machine job. Note that this also deletes all respective artifacts and is non-reversible. Accepts no arguments.

* *Example: **

`1 2` ` job = MMT("data-job", teamspace="my-teamspace", org="my-org") job.delete()`

## status[](#status)

Property returning the current status of the multi-machine job.

* *Example: **

`1 2` ` job = MMT("data-job", teamspace="my-teamspace", org="my-org") print(job.status) # -> Status.Pending, Status.Running, Status.Completed, Status.Stopped, Status.Failed`

## machine[](#machine)

Property returning the machine the multi-machine job is/was running on.

* *Example: **

`1 2` ` job = MMT("data-job", teamspace="my-teamspace", org="my-org") print(job.machine) # -> Machine.A10G`

## machines[](#machines)

Property returning objects referring to the individual machines the job is running on

## artifact\_path[](#artifactpath)

Property returning the path the artifacts are saved to.

* *Example: **

`1 2` ` job = MMT("data-job", teamspace="my-teamspace", org="my-org") print(job.artifact_path) # -> "/teamspace/jobs/data-job/artifacts"`

## snapshot\_path[](#snapshotpath)

Property returning the path the multi-machine job snapshot is saved to.

* *Example: **

`1 2` ` job = MMT("data-job", teamspace="my-teamspace", org="my-org") print(job.snapshot_path) # -> "/teamspace/jobs/data-job/snapshot"`

## name[](#name)

Property returning the name of the multi-machine job.

* *Example: **

`1 2` ` job = MMT("data-job", teamspace="my-teamspace", org="my-org") print(job.name) # -> "data-job"`

## teamspace[](#teamspace)

Property returning the teamspace the multi-machine job belongs to.

* *Example: **

`1 2` ` job = MMT("data-job", teamspace="my-teamspace", org="my-org") print(job.teamspace) # -> Teamspace("my-teamspace", org="my-org")`

## studio[](#studio)

Property returning the studio used as compute environment if it wasn't launched with a docker image.

* *Example: **

`1 2` ` job = MMT("data-job", teamspace="my-teamspace", org="my-org") print(job.studio) # -> Studio("my-studio", teamspace="my-teamspace", org="my-org") or None`

## image[](#image)

Property returning the image used as compute environment if it wasn't launched with a Studio.

* *Example: **

`1 2` ` job = MMT("data-job", teamspace="my-teamspace", org="my-org") print(job.image) # -> "ubuntu:latest" or None`

## command[](#command)

Property returning the command ran within the multi-machine job.

* *Example: **

`1 2` ` job = MMT("data-job", teamspace="my-teamspace", org="my-org") print(job.command) # -> "python train.py"`

## logs[](#logs)

Property returning the logs generated by running the multi-machine job. Will return an error if the job is still pending or running \(check [job.status](https://lightning.ai/docs/overview/batch-jobs/sdk-reference#status) \)

* *Example: **

`1 2` ` job = MMT("data-job", teamspace="my-teamspace", org="my-org") print(job.logs) # -> "Epoch 1/2: ################"`

## link[](#link)

Property returning the link to view the job in the UI.

* *Example: **

`1 2` ` job = MMT("data-job", teamspace="my-teamspace", org="my-org") print(job.link) # -> "https://lightning.ai/my-org/my-teamspace/studios/my-studio/app?app_id=jobs&job_name=data-job"`

