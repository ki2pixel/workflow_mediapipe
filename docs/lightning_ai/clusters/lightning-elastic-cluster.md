# Lightning elastic cluster[](#lightning-elastic-cluster)

Lightning Elastic Cluster \(LEC\) is a fully managed, multi-cloud cluster purpose-built for AI. It combines on-demand elasticity with reserved capacity, so clusters can run 100% on-demand, 100% reserved, or anywhere in between.

LEC brings the flexibility of Kubernetes and SLURM into a single system - without maintaining layers of extra operators, YAML configs, or multi-scheduler workarounds. Training, inference, development, and pipelines all run side by side as first-class workloads.


Select an Image

## Why Lightning Elastic Cluster[](#why-lightning-elastic-cluster)

Today, most ML teams are caught between tools built for different eras. Kubernetes is excellent at orchestrating stateless services, and SLURM has long been the standard for HPC and training workloads. But neither covers the entire AI lifecycle out of the box. That leaves researchers dealing with infra overhead and DevOps maintaining multi-scheduler stacks with clusters ending up underutilized because machines sit idle between jobs.

Lightning Elastic Cluster was created to close this gap. It makes the idea of a “cluster” elastic by default: compute grows and shrinks with demand, workloads can span multiple clouds, and every type of ML job - training, inference, dev loops, pipelines, and data prep - shares the same simple abstraction. Instead of piecing systems together, you get one environment that just works.

## What it gives you[](#what-it-gives-you)

LEC combines the reliability of traditional schedulers with the elasticity and ML-awareness that modern workloads demand. Multi-node training jobs can be launched without manually setting up clusters. Inference servers autoscale and recover from failures automatically. Interactive development runs alongside batch jobs without extra tooling. And GPUs are managed throughout their lifecycle - shared when possible, dedicated when needed, and reclaimed when idle - so utilization stays high without manual over-provisioning.

Because everything runs through the same interface, teams can easily move from development to production. A researcher can experiment in a Lightning Studio and submit the same code as a job when it’s ready. Infra teams can add guardrails like RBAC, audit logs, and usage limits without slowing anyone down. Workloads can even be composed into pipelines, chaining training, serving, and post-processing in a single flow.

## How it's different[](#how-its-different)

General-purpose orchestrators were not built with AI in mind. Lightning Elastic Cluster is. It understands training loops, checkpointing, and inference traffic patterns. It’s optimized for GPUs, with features like GPU sharing, NUMA pinning, and preemptible recovery. It gives you both high-level simplicity for researchers who want to avoid YAML and Docker, and low-level control for engineers who want to tune every detail. And it integrates with existing Kubernetes or SLURM environments, so you can adopt it workload by workload without abandoning what you already have.

## Maximize GPU utilization[](#maximize-gpu-utilization)

With LEC, organizations see higher GPU utilization, faster iteration for researchers, and less time spent maintaining brittle infrastructure. DevOps is freed from juggling multiple schedulers, while researchers get self-serve environments that match their workflows. Collaboration improves because workloads are defined with a shared abstraction instead of one-off scripts. And because LEC is elastic and multi-cloud, teams can scale up for billion-parameter training runs or scale down for classroom projects—on the same platform.

## Getting started with LEC[](#getting-started-with-lec)

To use LEC, first, reserve a GPU cluster by contacting sales@lightning.ai and request that your cluster be provisioned with the LEC.

## Developer experience[](#developer-experience)

Developers can interact with an LEC cluster using the same K8s or SLURM syntax they're used to. YAMLs, configs, etc... can all interface without changes with LEC. However, for developers who want a simpler experience and don't want to learn K8s or SLURM, Lightning offers a simpler, dev-friendly syntax to submit jobs/interact with the LEC cluster via the CLI.

## Summary[](#summary)

Lightning Elastic Cluster is the AI-native alternative to SLURM and Kubernetes:

  - ✅ Unified system for training, inference, batch jobs

  - ✅ Built-in autoscaling, GPU scheduling, fault tolerance

  - ✅ Seamless integration with Lightning Studios and SDK

  - ✅ Enterprise-grade control without slowing down researchers


No infrastructure to manage. No YAML to fight. Just jobs that run.

