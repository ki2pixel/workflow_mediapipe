# Scheduling[](#scheduling)

Pipelines can be scheduled either through the Lightning UI or directly via the Lightning SDK.

# From the SDK[](#from-the-sdk)

This script demonstrates how to set up an automated pipeline using the Lightning SDK. The pipeline, named 'cron', executes a Python script, "main.py", within a Studio environment. It is configured to run repeatedly, with a schedule set to trigger the execution every minute using a cron expression. The setup process involves initializing the pipeline, defining the job execution steps, and establishing a schedule for the pipeline to automate its run at the specified intervals.

Initialize the Pipeline

We start by importing necessary classes from the lightning\_sdk and create an instance of the Pipeline class with the name 'cron'.

Define Pipeline Steps

Next, we define the steps that the pipeline should execute. In this example, we are running a single Studio Job. The Job executes the command "python main.py" within the Studio environment.

Schedule Pipeline Execution

Finally, we schedule the pipeline to run at specified intervals. The schedule used here is "\* \* \* \* \ *", which configures the pipeline to run every minute.

`1 2 3 4 5 6 7 8 9 10 ` ` from lightning_sdk.pipeline import Pipeline, JobStep, Studio, Schedule  pipeline = Pipeline(name='cron') pipeline.run( steps=[ JobStep(command="python main.py", studio=Studio()), ], schedules=[Schedule(" * ** * *")] )`

Notes:

  1. For the time being, Lightning pipelines can be created only the SDK. However, you can configure your scheduling from the UI once created.

  2. From the SDK, the schedule timezone defaults to UTC.


Notes:

  1. For the time being, Lightning pipelines can be created only the SDK. However, you can configure your scheduling from the UI once created.

  2. From the SDK, the schedule timezone defaults to UTC.


# From the UI[](#from-the-ui)

In the UI, navigate to the Schedules Tab, where you'll find the ` New Schedule ` button in the top right corner. Clicking this button allows you to easily configure your schedule through Lightning's user-friendly interface. Alternatively, you can use the traditional cron format for specifying schedules.

https://pl-flash-data.s3.us-east-1.amazonaws.com/pipeline-scheduling.mp4

Video showing how to create a pipeline schedule

Notes:

  1. From the UI, you can configure the scheduling timezone. By default, it uses the browser's timezone but you can manually change it.

  2. From the UI, you can stop or delete a schedule whenever you need to.


