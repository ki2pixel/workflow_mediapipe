# Multi-Machine jobs[](#multi-machine-jobs)

The ` mmt(s) ` commands in the lightning command line interface \(CLI\) allow you to create new multi-machine jobs and interact with existing jobs. Use this to offload tasks like data processing, training runs, or inference jobs that do not require interactive execution but multiple machines.

The CLI is automatically available inside Studios. To use the CLI outside a Studio, install it with:

`1 ` ` pip install --upgrade lightning-sdk`

Ensure you authenticate using environment variables or login via CLI.

`1 2 3 4 5 6 ` ` export LIGHTNING_USER_ID=your-user-id export LIGHTNING_API_KEY=your-api-key # or lightning login`

## Submit a Multi-Machine Job[](#submit-a-multi-machine-job)

To submit a job, use the following command:

`1 ` ` lightning run mmt --command="python my-command"`

The following flags/options are available:

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

\--name

str

The name of the job

date-time encoded job name

\--machine

str

Machine to run the Job on

CPU

\--num-machines, --num\_machines

int

The number of machines to run the job on

2

`--command`

`str`

The command to run inside the Studio

None, The command to run inside your job. Required is using a Studio as compute environment. Optional for docker jobs. In case it's not specified for docker jobs, these will run the default command specified by the image.

\--studio

str

The studio env to run the job with. Mutually exclusive with image.

None, Inferred from environment in case image is not specified.

\--image

str

The docker image to run the job with. Mutually exclusive with studio.

None

\--teamspace

str

The teamspace the job should be associated with.

None, Inferred from the studio if used as compute environment, else inferred from environment.

\--org

str

The organization owning the teamspace \(if any\).

None, inferred from either Studio \(if used as compute environment\), teamspace \(if provided\) or environment.

\--user

str

The user owning the teamspace \(if any\).

None, inferred from either Studio \(if used as compute environment\), teamspace \(if provided\) or environment.

\--cloud-account, --cloud\_account

str

The cloud acocunt to run the job on

None, inferred from the Studio \(if used as compute environment\) or environment if possible. Falls back to teamspace default cloud-account otherwise.

\--env, -e

str

Environment variables to set inside the job. Can be specified multiple times. Once per env-var of type ` KEY=VALUE`

None

\--interruptible

bool

If specified, runs job on interruptible instances. They are cheaper but can be preempted.

False if not set

\--image-credentials, --image\_credentials

str

The credentials used to pull the image. Required if the image is private. This should be the name of the respective credentials secret created on the Lightning AI platform.

None

\--cloud-account-auth, --cloud\_account\_auth

bool

If specified, authenticates with the cloud account to pull the image. Required if the registry is part of a cloud provider \(e.g. ECR\).

False if not set

entrypoint

str

The entrypoint of your docker container. To use the pre-defined entrypoint of the provided image, set this to an empty string. Only applicable when submitting docker jobs.

"sh -c", which just runs the provided command in a standard shell.

\--path-mapping, --path\_mapping

str

Mapping of data-connections to paths inside the container. Can be specified multiple times \(once per mapping\). Should be of format ` <CONTAINER_PATH>:<CONNECTION_NAME>:<PATH_RELATIVE_TO_CONNECTION_ROOT> ` . If the last part \( ` :<PATH_RELATIVE_TO_CONNECTION_ROOT> ` \) is omitted, it will behave as if it was specified with ` :/ ` \(meaning the root of the connection will be mounted\). Only applicable to docker jobs, as studio jobs will have the regular teamspace filesystem and thereby access to all data-connections anyways.

None

## List Running Multi-Machine Jobs[](#list-running-multi-machine-jobs)

To list existing multi-machine run

`1 ` ` lightning list mmts`

The following options are available for this command:

Add row above

Add row below

Delete row

Add column to left

Add column to right

Delete column

* *Flag **

* *Type **

* *Description **

* *Default **

\--teamspace

str

The Teamspace to list jobs from. Should be specified as ` <OWNER>/<NAME> ` . Mutually exclusive with --all

None, can be selected from an interactive menu if not specified.

\--all

bool

List jobs across all Teamspaces. Mutually exclusive with --teamspace

False, if flag not set

\--sort-by, --sort\_by

str

Specifies by which attribute the jobs should be sorted.

Sort jobs by name.

## Stop a Job[](#stop-a-job)

To stop a running job run:

`1 ` ` lightning stop mmt MY-JOB-NAME`

This command accepts the following options:

Add row above

Add row below

Delete row

Add column to left

Add column to right

Delete column

Flag

Type

Description

Default

\--teamspace

str

The Teamspace to list jobs from. Should be specified as ` <OWNER>/<NAME> ` .

None, will be inferred from environment if possible and can be selected from an interactive menu otherwise if not specified.

## Delete a Multi-Machine Job[](#delete-a-multi-machine-job)

To delete an existing job run:

`1 ` ` lightning delete mmt MY-JOB-NAME`

Note: This will delete the associated artifacts as well.

This command accepts the following options:

Add row above

Add row below

Delete row

Add column to left

Add column to right

Delete column

Flag

Type

Description

Default

\--teamspace

str

The Teamspace to list jobs from. Should be specified as ` <OWNER>/<NAME> ` .

None, will be inferred from environment if possible and can be selected from an interactive menu otherwise if not specified.

