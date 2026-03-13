# Storage[](#storage)

Lightning created PyTorch Lightning in 2019 to train large-scale models at Facebook AI on thousands of GPUs. We’ve spent years tuning data pipelines where any slowdown in disk or network I/O can waste millions in GPU hours. This expertise is built into Lightning’s platform - so your foundation model training jobs never get bottlenecked by storage.

On the platform we offer various options.

# Development[](#development)

## Teamspace filesystem[](#teamspace-filesystem)

For devboxes \(Studios\) and interactive development, Lightning teamspaces include a shared, cloud-agnostic distributed filesystem. All team members can move files instantly between Studios, even across different clouds. Start on Lambda Labs, finish on Nebius... your data follows you seamlessly. Lightning handles all egress/ingress behind the scenes to keep latency low and throughput high.

## Bring data[](#bring-data)

Your data may already live in S3, EFS, GCS, Snowflake, or another store. Lightning connects to these sources directly with no unnecessary copies, while tuning your training pipeline to avoid bottlenecks from slow remote reads. We can stage hot data to NVMe or RAM caches so GPUs are never waiting.

## Cloud folders[](#cloud-folders)

Lightning has a very easy way to create cloud folders on any cloud. Simply find the "Drive" button in your teamspace, and then choose between uploading data, S3, EFS, filestore, GCS, our our proprietary cloud-agnostic folders. The same folder can be mounted from multiple regions and clouds without manual sync.

# High-performance training[](#high-performance-training)

When we configure an HPC cluster for your training run, Lightning selects the fastest storage tier available. We match it to your interconnect \(InfiniBand, RoCE, 400G Ethernet\) to guarantee full GPU utilization. We benchmark and tune for hundreds of GB/s throughput and sub-millisecond latency at scale.

## Weka, Vast data[](#weka-vast-data)

We integrate with leading high-performance storage systems like Weka, Vast Data, Lustre, GPFS, and work with your preferred vendor to ensure optimal configuration. Our team can also recommend hierarchical caching \(NVMe + RAM + object storage\) and automatic dataset sharding to keep thousands of GPUs saturated without stalls.

# Security and compliance[](#security-and-compliance)

For sensitive or proprietary datasets, Lightning supports encryption in transit and at rest, along with compliance for HIPAA, GDPR, and SOC 2 environments, so you can scale securely.

