# Versioning[](#versioning)

Pipelines are versioned automatically, so each time you re-execute your script, a new version is created.

# First execution[](#first-execution)

`1 2 3 4 5 6 7 8 9 10 11 12 ` ` from lightning_sdk.pipeline import Pipeline, JobStep, Studio studio = Studio(name="demo") hello_world_job = JobStep( command="python main.py", studio=studio ) pipeline = Pipeline(name='hello_world_pipeline') pipeline.run(steps=[hello_world_job]) `

When you run the code for the first time, you will see the initialization of the Studio environment, the cloning of the "pipeline demo" repository, and the execution of the training and deployment jobs within a newly created pipeline. The outputs of each step, including any logs or results, will be displayed in the console or interface, providing feedback on the process and verifying successful execution.

`1 2 3 4 5 6 7 8 9 10 11 12 13 14 15 16 17 18 19 20 ` ` ──────────────────────────────────────────────────────────── ✅ Pipeline 'hello_world_pipeline' created successfully! ──────────────────────────────────────────────────────────── Workflow Steps: ➡️ 1. Job 'step-0' - (runs first) 🗓️ Schedules: - No schedules defined. Cloud account: - yabbering-purple-59op Shared filesystem: True - /teamspace/s3_folders/pipelines-yabbering-purple-59op ──────────────────────────────────────────────────────────── 🔗 View your pipeline in the browser: http://lightning.ai/lightnin-ai/pipelines-demo/pipelines/hello_world_pipeline?app_id=pipeline ────────────────────────────────────────────────────────────`

https://pl-flash-data.s3.us-east-1.amazonaws.com/pipeline-simple-version-0.mp4

The resulting pipeline created after the code has been executed

# Further executions[](#further-executions)

Upon re-executing this code, it indicates that the pipeline has been updated, resulting in the creation of a new version. This ensures that each run is tracked and documented, providing a history of changes and executions.

`1 2 3 4 5 6 7 8 9 10 11 12 13 14 15 16 17 18 19 20 ` ` ──────────────────────────────────────────────────────────── ✅ Pipeline 'hello_world_pipeline' updated successfully! ──────────────────────────────────────────────────────────── Workflow Steps: ➡️ 1. Job 'step-0' - (runs first) 🗓️ Schedules: - No schedules defined. Cloud account: - yabbering-purple-59op Shared filesystem: True - /teamspace/s3_folders/pipelines-yabbering-purple-59op ──────────────────────────────────────────────────────────── 🔗 View your pipeline in the browser: http://lightning.ai/lightnin-ai/pipelines-demo/pipelines/hello_world_pipeline?app_id=pipeline ────────────────────────────────────────────────────────────`

https://pl-flash-data.s3.us-east-1.amazonaws.com/pipeline-version-2.mp4

The resulting pipeline after the code has been executed twice

