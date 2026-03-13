# Job pipeline \(DAG\)[](#job-pipeline-dag)

Jobs in Lightning run asynchronously by default. To create a job pipeline where jobs run sequentially, you need to monitor the ` status ` attribute of the ` Job ` object and trigger subsequent jobs based on the completion of preceding ones.

## Sequential pipeline example[](#sequential-pipeline-example)

Here’s how to create a pipeline that runs a data preparation job followed by a training job:

`1 2 3 4 5 6 7 8 9 10 11 12 13 14 15 16 17 18 19 20 21 ` ` from lightning_sdk import Studio, Machine, Status, Job import time # Initialize Studio and access the Jobs plugin studio = Studio(name="my-studio", teamspace="my-teamspace", user="my-user") # Submit the data preparation job data_prep_job = Job.run(command="python data_prep.py", name="data-job", machine=Machine.DATA_PREP, studio=studio) print(data_prep_job.status) # -> Status.Pending # Wait for the data prep job to finish while data_prep_job.status in [Status.Pending, Status.Running]: time.sleep(60) print(f"Data prep job finished with status: {data_prep_job.status}") # Submit the training job once the data prep is complete if data_prep_job.status == Status.Completed: train_job = Job.run(command="python train.py", name="train-job", machine=Machine.L40S, studio=studio) else: print(f"Data prep job failed with status: {data_prep_job.status}")`

## Job statuses[](#job-statuses)

Jobs can have one of the following statuses:

Add row above

Add row below

Delete row

Add column to left

Add column to right

Delete column

Status

Description

Pending

Waiting to be executed.

Running

Currently being executed.

Failed

The job encountered an error and did not complete successfully.

Stopped

The job was manually stopped.

Completed

The job finished successfully.

## Multi-machine training[](#multi-machine-training)

For advanced workflows like multi-machine training \(MMT\), use the ` multi-machine-training ` plugin. Learn more about this in our [hyperparameter tuning guide](https://lightning.ai/docs/overview/Studios/sdk#find-the-best-hyperparameters-for-a-model) .

