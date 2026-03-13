# Multi-node Inference[](#multi-node-inference)

Certain AI models require a specialized type of deployment which is multi-node inference. This is trivial to set up on Lightning Deployments.

https://pl-bolts-doc-images.s3.us-east-2.amazonaws.com/app-2/Deploy\_Multinode.mp4

Lightning automatically sets all necessary environment variables to properly configure multi-node inference and ensures seamless collaboration between nodes.

Here are the environment variables:

Add row above

Add row below

Delete row

Add column to left

Add column to right

Delete column

* *Name **

* *Description **

MASTER\_ADDR

The address of the main node.

MASTER\_PORT

The port of the main node.

WORLD\_SIZE

The total number of available devices.

NODE\_RANK

The rank of the current node.

NUM\_NODES

The total number of available nodes.

## Example: SGLang multi-node inference[](#example-sglang-multi-node-inference)

This example demonstrates how the container’s bash start script passes environment variables to [sglang](https://github.com/sgl-project/sglang) to enable multi-node inference for a given model.

### Dockerfile[](#dockerfile)

`1 2 3 4 5 6 7 8 9 ` ` # Dockerfile FROM lmsysorg/sglang:latest RUN pip install litmodels WORKDIR /app COPY . . ENTRYPOINT ["/app/start.sh"]`

### Bash start script [](#bash-start-scriptandnbsp)

`1 2 3 4 5 6 7 8 ` ` # /app/start.sh #!/bin/bash LIGHTNING_CLOUD_URL=https://lightning.ai lightning download model "${MODEL_NAME}" --download_dir=${MODEL_DIR} echo "python3 -m sglang.launch_server --dist-init-addr ${MASTER_ADDR}:5000 --nnodes ${NUM_NODES} --node-rank ${NODE_RANK} --trust-remote-code --model-path ${MODEL_DIR} $@" exec python3 -m sglang.launch_server --dist-init-addr ${MASTER_ADDR}:5000 --nnodes ${NUM_NODES} --node-rank ${NODE_RANK} --trust-remote-code --model-path ${MODEL_DIR} "$@"`

