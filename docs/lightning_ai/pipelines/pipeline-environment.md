# Pipeline environment[](#pipeline-environment)

When setting up Pipelines, you have the option to use either a Studio environment or a container as the source for the pipeline's execution environment.

# Using a Studio[](#using-a-studio)

In the example below, the pipeline utilizes the Studio environment to manage the execution of a job.

Initialize the Pipeline

We start by importing necessary classes from the lightning\_sdk and create a Studio named 'studio\_env'.

Define Pipeline

Next, we create a pipeline instance named 'pipeline\_from\_studio' that will inherit from the Studio environment. we define the steps that the pipeline should execute.

Define steps

In this example, we are running a single Studio Job. The Job executes the command "python main.py" within the Studio environment.

`1 2 3 4 5 6 7 8 9 10 ` ` from lightning_sdk.pipeline import Pipeline, JobStep, Studio  studio = Studio(name="studio_env") pipeline = Pipeline(name='pipeline_from_studio', studio=studio) pipeline.run( steps=[ JobStep(command="python main.py"), ], )`

# Using a container[](#using-a-container)

Initialize the Pipeline

We start by importing necessary classes from the lightning\_sdk

Define Pipeline

Next, we create a pipeline instance named 'container\_pipeline'

Define steps

We are running a single container Job. The Job executes the command "echo 'Hello, World\!'" within the container.

`1 2 3 4 5 6 7 8 9 10 11 12 ` ` from lightning_sdk.pipeline import Pipeline, JobStep  pipeline = Pipeline(name='container_pipeline') pipeline.run( steps=[ JobStep( image="ubuntu:latest", command="echo 'Hello, World!'" ) ] )`

