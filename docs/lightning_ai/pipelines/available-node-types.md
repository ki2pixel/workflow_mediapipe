# Available node types[](#available-node-types)

Pipelines can be made up of Jobs, Deployments or multi-node \(MMT\) jobs.

# Types[](#types)

Add row above

Add row below

Delete row

Add column to left

Add column to right

Delete column

* *Name **

* *Action **

JobStep

Create a new Job when the step is executed

MMTStep

Create a new MMT Job when the step is executed

DeploymentStep

Create a new Deployment Job when the step is executed

DeploymentReleaseStep

Create a new Release over an existing deployment when the step is executed

## Code[](#code)

`1 2 3 4 5 6 7 8 9 10 11 12 13 14 15 16 17 18 19 20 21 22 23 24 25 26 27 ` ` from lightning_sdk.pipeline import Pipeline, JobStep, MMTStep, DeploymentStep from lightning_sdk.machine import Machine pipeline = Pipeline(name='third-pipeline') pipeline.run( steps=[ JobStep( name='job-1', image="ubuntu:latest", machine=Machine.CPU, command="sleep 9 && echo 'Hello, World!'" ), MMTStep( name='mmt-2', image="ubuntu:latest", machine=Machine.CPU, command="echo 'Hello, World!'", wait_for=None, ), DeploymentStep( name='deployment-3', image="nginx", machine=Machine.CPU, ports=[8000], ), ] )`

`1 2 3 4 5 ` ` ===== Generated Pipeline ===== 0 - Job['job-1'] wait_for nothing 1 - MMT['mmt-2'] wait_for nothing 2 - Deployment['deployment-3'] wait_for ['job-1', 'mmt-2'] ===== ================== =====`

## The resulting Pipeline[](#the-resulting-pipeline)


Select an Image

