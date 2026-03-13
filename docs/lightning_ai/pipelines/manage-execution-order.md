# Manage execution order[](#manage-execution-order)

The ` wait_for ` argument defines the dependencies of a step within the pipeline.

  - If ` wait_for=None ` , the step has no dependencies and will start executing immediately.

  - If a step does not explicitly set ` wait_for ` , it will automatically depend on all preceding steps in the pipeline.


## Code[](#code)

`1 2 3 4 5 6 7 8 9 10 11 12 13 14 15 16 17 18 19 20 21 22 23 24 25 26 27 ` ` from lightning_sdk.pipeline import Pipeline, JobStep from lightning_sdk.machine import Machine pipeline = Pipeline(name='second-pipeline') pipeline.run( steps=[ JobStep( name='job-1', image="ubuntu:latest", machine=Machine.CPU, command="sleep 9 && echo 'Hello, World!'" ), JobStep( name='job-2', image="ubuntu:latest", machine=Machine.CPU, command="sleep 9 && echo 'Hello, World!'", wait_for=None ), JobStep( name='job-3', image="ubuntu:latest", machine=Machine.CPU, command="sleep 9 && echo 'Hello, World!'", ), ] )`

## The resulting Pipeline[](#the-resulting-pipeline)

`1 2 3 4 ` ` ===== Generated Pipeline ===== 0 - Job['job-1'] wait_for nothing 1 - Job['job-2'] wait_for nothing 2 - Job['job-3'] wait_for ['job-1', 'job-2']`


Select an Image

