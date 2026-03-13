# Managed Kubernetes[](#managed-kubernetes)

Lightning supports fully managed Kubernetes clusters, so you can keep running your existing workloads - while gaining visibility, reliability, and control designed for AI/ML teams.

Whether you're running model inference servers, batch jobs, or custom microservices, Lightning gives you the Kubernetes foundation you’re used to - with built-in support for team-scale collaboration and modern AI workflows.

## Why Kubernetes?[](#why-kubernetes)

Kubernetes is widely used across the industry for container orchestration and is a natural choice for:

  - Running model inference as microservices

  - Deploying REST APIs and web applications

  - Managing autoscaling, service discovery, and fault tolerance


If your team already has a Kubernetes-based workflow, Lightning ensures you can continue using it without changes - and without managing the underlying infrastructure.

## Our opensouce works with K8s[](#our-opensouce-works-with-k8s)

All Lightning open-source tools can be containerized and deployed to Kubernetes. You can run training, inference, or hybrid workloads as custom Kubernetes jobs and services.

Lightning also supports native integration with tools like:

  - Helm charts

  - Argo Workflows

  - KubeFlow

  - Any custom Kubernetes operators


You’re not locked in - and you don’t have to rebuild anything.

## Lightning enhances Kubernetes[](#lightning-enhances-kubernetes)

Lightning makes Kubernetes easy to work with for teams and real use-cases:

  - Managed GPU infrastructure with full autoscaling and node health monitoring

  - Observability across pods, nodes, and services \(UI + APIs\)

  - Team management \(RBAC, audit logs, usage tracking\)

  - Integrated storage and secrets management

  - Optional migration path to Lightning Orchestrator for multi-node training and AI-native workloads

  - Support for hybrid SLURM + Kubernetes deployments


## Same workflow[](#same-workflow)

Use the same workflow and tools you're used to

`1 ` ` kubectl apply -f inference-deployment.yaml`

## When to use Lightning orchestrator[](#when-to-use-lightning-orchestrator)

Kubernetes is powerful - but it wasn’t built with model training or multi-GPU inference in mind.

If you start to hit:

  - Difficulty managing multi-node training jobs

  - Instability with model training

  - Poor GPU utilization due to pod scheduling constraints

  - Inference workloads that don’t autoscale correctly

  - Researcher frustration with having to learn k8s concepts

  - Complex infra needs for hybrid serving + training systems


…you can move specific workloads to the Lightning Orchestrator, which offers a familiar job-style interface built for AI. The rest of your Kubernetes workflows can remain untouched.

