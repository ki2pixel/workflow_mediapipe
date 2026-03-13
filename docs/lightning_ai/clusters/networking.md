# Networking[](#networking)

In large-scale training, the wrong network setup can silently cut your throughput in half and waste millions in GPU time. Lightning’s team learned this firsthand building PyTorch Lightning in 2019 and running thousands of GPUs at Facebook AI. By 2020, we were among the first to understand that cloud training required co-located compute and storage workloads with high-speed interconnects,_years before this became standard practice_ , because we saw how critical it was for scaling.

Today, that experience is baked into Lightning’s platform. We design networking from the ground up to keep GPUs fully saturated, even when training trillion-parameter models.

## Cloud partner selectivity[](#cloud-partner-selectivity)

Lightning only onboards clouds that meet our fast networking criteria - ensuring HPC-grade fabrics, predictable performance, and low-latency links to storage. We partner with the best cloud providers globally and run extensive benchmarks before making them available to customers. For each supported cloud, we maintain optimal configuration blueprints that align the interconnect, topology, and storage integration for maximum GPU utilization.

## HPC-grade interconnects[](#hpc-grade-interconnects)

When we partner with clouds and provide clusters, we don’t just “add GPUs” - we engineer the network fabric to match your workload. Lightning supports:

  - InfiniBand HDR / NDR / NDR400 for ultra-low latency, lossless communication

  - 400G and 200G RoCE v2 Ethernet tuned for RDMA performance

  - Hybrid fabrics combining InfiniBand for training and Ethernet for storage access


We tune your cluster to deliver consistent microsecond-scale latency and maximize effective bandwidth, ensuring allreduce, gradient exchange, and parameter synchronization happen without GPU stalls.

## Topology-aware placement[](#topology-aware-placement)

We map workloads to the network topology so nodes that communicate most frequently are placed on the same switch fabric or leaf-spine segment, avoiding unnecessary hops. For FSDP, Megatron-LM, and DeepSpeed jobs, we align the model parallel groups with the network layout for peak throughput.

## Collocation and data proximity[](#collocation-and-data-proximity)

In 2020, we pioneered setting up AWS clusters with collocated compute and data storage within the same availability zone and rack groups on AWS, eliminating cross-AZ traffic, avoiding multi-hop penalties, and allowing GPUs to stream training batches at full interconnect speed. Today, Lightning automates this placement for optimal locality, even in multi-thousand GPU deployments.

## Optimized NCCL and collective operations[](#optimized-nccl-and-collective-operations)

Lightning clusters ship with NCCL tuned for your specific fabric, whether InfiniBand or RoCE, so collective operations like allreduce and allgather run at peak efficiency. We benchmark and adjust parameters \(tree vs ring algorithms, buffer sizes, channel counts\) to fit your model’s needs.

## Multi-cloud networking[](#multi-cloud-networking)

Because Lightning is cloud-agnostic, we abstract away differences between each provider’s networking stack while still delivering HPC-grade performance. Across our 8+ partner clouds, we ensure:

  - Optimal inter-node bandwidth for large-scale model training

  - Dedicated network partitions for predictable performance

  - Low-latency, high-throughput paths between compute and storage


## Security at Line Rate[](#security-at-line-rate)

Lightning supports encryption in transit \(IPsec, TLS, or provider-native\) without degrading performance, so sensitive datasets move across fabrics without sacrificing speed.

## Proven at extreme scale[](#proven-at-extreme-scale)

Our networking designs have been used to train foundation models with thousands of GPUs, petabytes of data, and multi-terabyte checkpoints - without network-induced slowdowns. The result: maximum GPU utilization, predictable training times, and lower cost per model trained.

