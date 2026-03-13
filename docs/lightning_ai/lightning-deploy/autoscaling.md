# Autoscaling[](#autoscaling)

A Lightning deployment can automatically scale to zero when idle \(serverless\), eliminating costs for unused resources. When demand spikes, it scales to manage increased traffic, ensuring high performance without manual adjustments.

# Scale to zero \(serverless\)[](#scale-to-zero-serverless)

Set minimum replicas to zero to enable _ * *scaling to zero * *_ , stopping all idle machines, which incurs no costs.

https://pl-bolts-doc-images.s3.us-east-2.amazonaws.com/Docs\_Studios\_MP4/DeployModels\_Autoscaling\_ScaletoZeroServerless\_ScaletoZero.mp4

Create a new serverless deployment with number of replicas between 0 and 1

By default, a machine auto-scales to zero if it doesn't receive any requests within 5 minutes. Feel free to modify this setting under the "advanced" section of the deployment configuration.

https://pl-bolts-doc-images.s3.us-east-2.amazonaws.com/Docs\_Studios\_MP4/DeployModels\_Autoscaling\_ScaletoZeroServerless\_5MinuteShutDown.mp4

A serverless deployment scaling down to zero after 5 minutes without any requests

You can change the default scale-down cooldown from 5 min to anything else.


https://pl-bolts-doc-images.s3.us-east-2.amazonaws.com/Docs\_Studios\_MP4/DeployModels\_Autoscaling\_ScaletoZeroServerless\_30secondadjustment.mp4

A serverless deployment scaling down to zero after 30 seconds without any requests

# Scale up[](#scale-up)

Set maximum replicas to be greater than 1 to automatically scale up during traffic surges.


https://pl-bolts-doc-images.s3.us-east-2.amazonaws.com/Docs\_Studios\_MP4/DeployModels\_Autoscaling\_ScaletoZeroServerless\_Scaleto1.mp4

By default, a deployment adds a new replica when CPU usage exceeds 95% for over 60 seconds.


Autoscaling section where the autoscaling metric can be modified

Select an Image

Lightning deployments supports 5 different autoscaling metrics:

Add row above

Add row below

Delete row

Add column to left

Add column to right

Delete column

Name

Definition

Autoscale from 0->N

CPU Utilization \(%\)

The CPU usage over the last minute.

No

GPU Utilization \(%\)

The GPU usage over the last minute.

No

Max concurrent requests

The maximum number of in-flight requests at any given time over the last minute.

Yes

Number of requests per minute \(RPM\)

The total number of completed requests over the last minute.

No

Latency \(ms\)

The average latency over the last minute.

No

Max concurrent requests is the only autoscaling metric that allows scaling directly from 0 to N, bypassing the intermediate step of scaling from 0 to 1 to N.


https://pl-bolts-doc-images.s3.us-east-2.amazonaws.com/Docs\_Studios\_MP4/DeployModels\_Autoscaling\_ScaletoZeroServerless\_Scaleto10.mp4

Set max concurrent requests to allow scaling directly from 0 to N.

# Cold starts[](#cold-starts)

A cold start refers to the time it takes for a deployment to get a new instance ready to receive traffic. Use the cold start explorer to identify and address bottlenecks during this process.


The cold start explorer displaying the time spent in getting a new instance ready to receive traffic.

Select an Image

When the deployment has been running for months, you can explore the global trends with more ease.


A serverless deployment running for multiple months

Select an Image

Cold starts often slow down due to bloated deployment images filled with unnecessary files, data, or large checkpoints. An easy win to speed up cold starts is to store model checkpoints on Lightning's optimized model hub and use Lightning's native container registry tailored for AI workloads.

Cold start is divided into 5 parts:

  1. * *Machine wait ** : The time the cloud provider takes to allocate a new machine. With a provisioned machine, this step is negligible.

  2. * *Machine start: ** The time by the machine to be ready. With provisioned machine, this step is negligible.

  3. * *Image pull: ** The time taken by the machine to pull the docker image. Using the Lightning registry, you can greatly reduce this step.

  4. * *Container start ** : The time taken by the container to start.

  5. Server ready: The time taken before the server is considered ready to receive traffic.


To ensure the server is properly marked as ready, configure a readiness health check.

