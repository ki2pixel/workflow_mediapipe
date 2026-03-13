# Managed SLURM[](#managed-slurm)

Lightning supports fully managed SLURM clusters so you can keep your existing training workflows - no changes required.

Whether you're running PyTorch DDP, TensorFlow, or custom shell scripts, Lightning gives you the SLURM interface you're used to, but with better reliability, visibility, and team management at scale.

## Why SLURM?[](#why-slurm)

SLURM is a battle-tested scheduler widely adopted for large-scale training jobs in academia and industry. It’s ideal for:

  - Multi-node training \(e.g., DDP, FSDP, DeepSpeed\)

  - Scheduling across heterogeneous GPU nodes

  - Controlling priority queues, fair-share policies, and job preemption


If you already have SLURM scripts and workflows, Lightning lets you run them as-is - without vendor lock-in or forced retooling.

## Our opensource works with SLURM[](#our-opensource-works-with-slurm)

All our open-source tools are SLURM aware and can work with SLURM clusters. Fun fact, PyTorch Lightning was built to work with fault-tolerance and autoscaling to train models across 2,000+ GPUs inside the Facebook AI research clusters in 2019. PyTorch Lightning has been battle-tested for over 6 years with over 200,000 contributor hours to make it the world's go-to framework for model training at scale.

## Lightning + SLURM[](#lightning-slurm)

Lightning turns SLURM clusters into fully-managed, secure clusters that are easy to manage at team scale.

  - Managed GPU infrastructure \(no setup or maintenance\)

  - Observability across jobs, nodes, and users \(UI + APIs\)

  - Team management and RBAC to control access and usage

  - Alerts for job failures, capacity bottlenecks, and stuck queues

  - Persistent storage across jobs and dev environments

  - Optional migration to Lightning Orchestrator for fault tolerance, autoscaling, and mixed-mode training/inference workflows


## SLURM workflow on Lightning[](#slurm-workflow-on-lightning)

Submit jobs using your existing SLURM scripts:

`1 ` ` sbatch train.sh`

or interactively:

`1 ` ` srun --gres=gpu:4 --cpus-per-task=8 --mem=64G python train.py`

## When to consider Lightning orchestrator[](#when-to-consider-lightning-orchestrator)

SLURM is great for batch training - but if you start to see:

  - Everyone using the same boxes and causing instability

  - SLURM software failures that take down the cluster

  - Cluster under-utilization \(because not everyone wants to be a SLURM expert\)

  - Long queue times

  - Complex scheduling for inference or hybrid workloads

  - Need for autoscaling or fault tolerance

  - Repeated job failures on preemptible hardware


…you can move specific workloads to the Lightning Orchestrator, which is built for AI-native patterns and have a similar interface to SLURM. The rest of your SLURM workflows can stay as-is.

