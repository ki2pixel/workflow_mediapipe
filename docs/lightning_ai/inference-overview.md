# Overview[](#overview)

Lightning offers a high-performance cloud at different levels of control, all the way from bare-metal to fully-managed Studios and clusters.

## On-demand[](#on-demand)

By default, everything you run on Lightning runs on-demand.

When you start a workload \(like a Studio or Job\) without reserving machines in advance, it runs on-demand. You pay only for the time you use. Availability for on-demand depends on supply and demand - popular GPU types may be temporarily sold out.

[Read more](https://lightning.ai/docs/overview/gpu-marketplace#on-demand)

## Reserved[](#reserved)

When workloads need guaranteed capacity or will run continuously, reserve instances in advance. You’ll get dedicated resources at reduced rates.

Contact our team to reserve instances \(support@lightning.ai\)

## GPU marketplace[](#gpu-marketplace)

Lightning's GPU marketplace lets you run any type of workload \(Studio, Job, Pipeline, Deployment, etc...\) on any cloud.


Select an Image

[Read more](https://lightning.ai/docs/overview/gpu-marketplace)

## Clusters[](#clusters)

Lightning offers high-performance GPU clusters with SLURM, Kubernetes or the Lightning Elastic Orchestrator.

Clusters allow teams to migrate their stacks as-is without changing workflow or code changes. Our managed clusters allow teams to maximize GPU utilization with full RBAC, observability, logs and more.

[Read more](https://lightning.ai/docs/overview/clusters)

## Bring your own cloud[](#bring-your-own-cloud)

Lightning lets organizations connect their cloud VPCs. This allows data to never leave your organization and to consume your cloud credits. This is great for startups with AWS/GCP credits and enterprises with pre-existing cloud commits.

Contact us to enable your private VPC \(support@lightning.ai\)

# Key benefits[](#key-benefits)

## Bring your own platform[](#bring-your-own-platform)

We find that mature ML teams have already built internal tooling stacks \(i.e., ‘ML platforms’\). Lightning lets you bring those platforms to our managed Kubernetes or SLURM clusters. We can help augment and simplify your workflows with ML-specialized runtimes - similar to pods in Kubernetes, but purpose-built for ML workloads - via Lightning Elastic Clusters.

Our ML specific runtimes \(similar to K8s pods\) are:

  - [Studios](https://lightning.ai/docs/overview/build-with-studios) \- development environment pod

  - [Jobs](https://lightning.ai/docs/overview/scale-with-batch-jobs) \- generic script submission

  - [Deployments](https://lightning.ai/docs/overview/deploy) \- deploys models with autoscaling

  - [MMT \(multi-node training\)](https://lightning.ai/docs/overview/pretrain-models) \- a specialized workload for training models on multiple-nodes

  - [LitData](https://lightning.ai/docs/overview/optimize-data/transform-data) \- a specialized workload for doing map operations with data


When you bring your own platform, Lightning gives you the ability to:

  - Run jobs exactly as you do today - no migration required

  - Bring your full stack

  - Onboard teams without introducing new tools

  - No new workflow required

  - Add RBAC, observability, alerts, and cost controls instantly

  - Alerts and observability layers on top of existing SLURM/Kubernetes


You get the familiar interface and control - with enterprise-grade management layered on top.

## Maximize GPU utilization[](#maximize-gpu-utilization)

Lightning can help you get the most out of your GPUs, no matter which orchestration system you use. Our tools layer on top of Kubernetes, SLURM, or Lightning elastic clusters to surface where utilization is falling short, and provide controls to manage usage at the cluster, workload, or even individual user level.

We often see teams averaging 50–60% utilization. With Lightning, they typically reach 70–80%+ by mapping the right workload to the right runtime. For example, using on-demand resources for development instead of keeping GPUs idle, we typically help customers save 40% or more on compute costs. The result is higher throughput for the same budget, and infrastructure that scales with your needs instead of holding you back.

## More elasticity as needed[](#more-elasticity-as-needed)

When SLURM or Kubernetes don’t provide the elasticity or scale you need for specific workloads - for example multi-cloud or on-demand - you can migrate individual workloads to Lightning elastic clusters, without rewriting code or changing tools.

* *For training: **

  - Supports multi-node and distributed jobs

  - Runs seamlessly from the same UI or CLI you're already using \(via Lightning Studios and Jobs\)


* *For inference: **

  - Autoscaling, fault tolerance, GPU sharing, multi-node inference, and more

  - Purpose-built primitives for AI workloads, not general web apps


Infra teams retain full control with the Lightning SDK for configuration and automation.

## Networking[](#networking)

In large-scale training, the wrong network setup can silently cut your throughput in half and waste millions in GPU time. Lightning’s team learned this firsthand building PyTorch Lightning in 2019 and running thousands of GPUs at Facebook AI. By 2020, we were among the first to understand that cloud training required co-located compute and storage workloads with high-speed interconnects,_ years before this became standard practice_, because we saw how critical it was for scaling. Today, that experience is baked into Lightning’s platform.

We design networking from the ground up to keep GPUs fully saturated, even when training trillion-parameter models.

[Read more](https://lightning.ai/docs/overview/clusters/networking) .

## Storage[](#storage)

Lightning created PyTorch Lightning in 2019 to train large-scale models at Facebook AI on thousands of GPUs. We’ve spent years tuning data pipelines where any slowdown in disk or network I/O can waste millions in GPU hours. This expertise is built into Lightning’s platform - so your foundation model training jobs never get bottlenecked by storage.

[Read more](https://lightning.ai/docs/overview/clusters/storage)

