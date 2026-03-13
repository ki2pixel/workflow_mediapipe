# Accelerate library[](#accelerate-library)

[Accelerate](https://huggingface.co/docs/accelerate) is an open source library that facilitates running training and inference workloads across multiple GPUs and multiple machines. It is developed by Hugging Face and released as open source software under the Apache 2.0 license.

Accelerate powers several projects from Hugging Face, among which:

  - Hugging Face [Transformers](https://github.com/huggingface/transformers)

  - Hugging Face [PEFT](https://github.com/huggingface/peft)

  - Hugging Face [TRL](https://github.com/huggingface/trl)


This guide applies to running scripts based on any of them. This includes libraries that build on top of Hugging Face Transformers such as:

  - [Unsloth](https://unsloth.ai)

  - [Axolotl](https://axolotl.ai)


 _ * *Note ** : If you are considering Accelerate for a new project, you might want to take a look at Lightning [Fabric](https://lightning.ai/docs/fabric/stable/) . It’s a lightweight library to scale PyTorch models without the boilerplate. Compared to Accelerate it aims to keep the magic low and to provide a greater level of control. Take a look at the end of this document for more details._

## Run Accelerate in a Studio[](#run-accelerate-in-a-studio)

Accelerate works out of the box on Lightning Studios. As in, your Accelerate code should work without modifications.

As an example, let’s consider the following sample code:

Import Accelerate

Most Accelerate features are provided through the Accelerator class

Set up the dataloader

In order to train a BERT classifier, we load samples from glue-mrpc dataset \(https://huggingface.co/sgugger/glue-mrpc\), tokenize them, and collate them into batches.

Instantiate Accelerator

We instantiate the main Accelerator object, specifying that training will happen using bfloat16 mixed precision, for faster training and lower memory usage.

Instantiate dataloader, model, and optimizer

We instantiate the dataloader with a batch size of 32, the BERT base cased model from Transformers, and the AdamW optimizer.

Pass model, optimizer and dataloader to Accelerate

We provide model, optimizer, and dataloader to Accelerate, the returned objects are aware of distributed strategies and mixed precision.

Run the training loop

The training loop is written like in plain PyTorch, with the exception of the call to backward.

Call backward through Accelerate

The only deviation from pure PyTorch is accelerator.backward\(\) vs loss.backward\(\), so Accelerate can manage the computation of the gradients.

`1 2 3 4 5 6 7 8 9 10 11 12 13 14 15 16 17 18 19 20 21 22 23 24 25 26 27 28 29 30 31 32 33 34 35 36 37 38 39 40 41 42 43 44 45 46 47 48 49 50 51 52 53 54 55 56 57 58 59 60 61 ` ` from datasets import load_dataset from torch.optim import AdamW from torch.utils.data import DataLoader from transformers import AutoModelForSequenceClassification, AutoTokenizer, DataCollatorWithPadding, set_seed  from accelerate import Accelerator. def get_dataloader(accelerator: Accelerator, batch_size: int): tokenizer = AutoTokenizer.from_pretrained("bert-base-cased") datasets = load_dataset("glue", "mrpc") def tokenize_function(examples): return tokenizer(examples["sentence1"], examples["sentence2"], truncation=True, max_length=None) with accelerator.main_process_first(): tokenized_datasets = datasets.map(tokenize_function, batched=True, remove_columns=["idx", "sentence1", "sentence2"], ) tokenized_datasets = tokenized_datasets.rename_column("label", "labels") collator = DataCollatorWithPadding(tokenizer=tokenizer, pad_to_multiple_of=8) train_dataloader = DataLoader( tokenized_datasets["train"], shuffle=True, batch_size=batch_size, collate_fn=collator, drop_last=True ) return train_dataloader  def main(): set_seed(seed=42) accelerator = Accelerator(mixed_precision="bf16") train_dataloader = get_dataloader(accelerator, batch_size=32) model = AutoModelForSequenceClassification.from_pretrained("bert-base-cased", return_dict=True) model = model.to(accelerator.device) model.train() optimizer = AdamW(params=model.parameters(), lr=1e-5) model, optimizer, train_dataloader = accelerator.prepare( model, optimizer, train_dataloader  ) num_epochs = 3 for epoch in range(num_epochs): for step, batch in enumerate(train_dataloader): batch.to(accelerator.device) optimizer.zero_grad() outputs = model( * *batch) loss = outputs.loss  accelerator.print(f"epoch/it {epoch}/{step}, train_loss: {loss}") accelerator.backward(loss) optimizer.step() accelerator.end_training() if * *name ** == " * *main * *": main()`

The code demonstrates training a basic BERT model on a classification task using HF Transformers. It was derived from this [example](https://github.com/huggingface/accelerate/tree/main/examples#simple-nlp-example) in the Accelerate codebase.

Start a new GPU Studio \(any GPU will do, L4 is a good choice\), and paste the code into the ` main.py ` file.

Install the dependencies:

`1 ` ` pip install accelerate datasets transformers`

And finally run the script:

`1 ` ` python main.py`

You will see training starting on the GPU automatically.

Now switch to a multi-GPU machine \(e.g. 4xL4\) and run ` python main.py ` again. You can see that the only the first GPU is utilized, while the others are left unused. This is because running across multiple GPUs requires launching the same code in separate processes—one for each GPU—and orchestrating the training using a distributed strategy.

In order to enable this, Accelerate comes with the ` accelerate launch ` command, a tool that facilitates launching training or inference scripts in distributed configurations. For example, running

`1 ` ` accelerate launch --num_processes 4 main.py`

on a machine with 4 GPUs, will launch four processes, each targeting one GPU, and distribute the training workload across them to accelerate model training. Please refer to the [documentation](https://huggingface.co/docs/accelerate/en/concept_guides/fsdp_and_deepspeed) for further details on the specific distributed strategies Accelerate supports.

Launching distributed scripts with ` accelerate launch ` is common to all libraries based on Accelerate, such as Hugging Face [Transformers](https://github.com/huggingface/transformers) , Hugging Face [PEFT](https://github.com/huggingface/peft) , and Hugging Face [TRL](https://github.com/huggingface/trl) .

This is valid for libraries that build on top of Hugging Face Transformers, such as [Unsloth](https://unsloth.ai) and [Axolotl](https://axolotl.ai) .

## Run Accelerate in a Job[](#run-accelerate-in-a-job)

As we just saw, ` accelerate launch ` runs without modifications on Lightning Studios. The same also applies to Jobs: just submit the ` accelerate launch ` command line directly as the job command, or wrap your ` accelerate launch ` command in a shell script \(say ` run.sh ` \) with the following content:

`1 ` ` accelerate launch --num_processes 4 main.py`

and use it as the command for the job. Keeping a script like ` run.sh ` is advised since Accelerate comes with several arguments, and keeping them in a script can be convenient. As a note, Accelerate also comes with the ability to generate configuration files in YAML format to store Accelerate arguments. Check out the documentation for [accelerate config](https://huggingface.co/docs/accelerate/v1.6.0/en/basic_tutorials/notebook#configuring-the-environment) to learn more.

## Run Accelerate in MMT jobs[](#run-accelerate-in-mmt-jobs)

Whereas using Accelerate in Studios and Jobs works out of the box, using it to run multi-machine training \(MMT\) jobs requires the user to provide a few extra flags to ` accelerate launch ` in order to inform Accelerate of the underlying distributed setup.

Suppose you want to run the training script distributed across 2 machines, with 4 GPUs each \(for a total of 8 processes, one for each GPU\).

Modify the ` run.sh ` script as in the following:

`1 2 3 4 ` ` accelerate launch --num_machines 2 --num_processes 8 \ --machine_rank $NODE_RANK --same_network \ --main_process_id $MASTER_ADDR --main_process_port $MASTER_PORT \ main.py`

and submit ` run.sh ` through the MMT plugin.

A downside of the above approach is that the user needs to modify the script whenever the number of machines or number of GPUs per machine change.

To avoid having to modify the ` run.sh ` script whether you are running in a Studio, Job, or MMT, you can make a few extra changes to the script that make it fully generic:

Determine GPUs per-node

Dynamically query the number of GPUs on a single machine

Compute launch parameters

Determine launch parameters for accelerate using the environment variables defined by MMT and the number of GPUs per machine

Launch script

Run the training script through accelerate launch so that the MMT cluster is fully utilized

`1 2 3 4 5 6 7 8 9 10 11 ` ` NUM_GPUS=$(nvidia-smi --query-gpu=name --format=csv,noheader | wc -l) NUM_PROCESSES=${WORLD_SIZE:-$NUM_GPUS} NUM_MACHINES=$((NUM_PROCESSES / NUM_GPUS)) MACHINE_RANK=${NODE_RANK:-0} MAIN_PROCESS_IP=${MASTER_ADDR:-localhost} MAIN_PROCESS_PORT=${MASTER_PORT:-63333} accelerate launch --num_machines $NUM_MACHINES --num_processes $NUM_PROCESSES \  --machine_rank $MACHINE_RANK --same_network \  --main_process_ip $MAIN_PROCESS_IP --main_process_port $MAIN_PROCESS_PORT \  main.py`

Running this script through the MMT plugin will scale training according to the machine type and number of machines selected in the plugin, without requiring further changes.

## Conclusions[](#conclusions)

Running training or inference scripts based on Hugging Face Accelerate is fully supported in Lightning Studios, Jobs, and MMT. Following this guide, you can run code based on Hugging Face Transformers, Peft, and Trl, as well as Unsloth and Axolotl on Lightning without modifications.

## One more thing[](#one-more-thing)

If you are looking for a lightweight library to power your next project, don’t forget to check out [Lightning Fabric](https://lightning.ai/docs/fabric/stable/) . Fabric allows you to use state-of-the-art features from PyTorch, like FSDP or model parallelism, without the boilerplate and with full control. Fabric has minimalistic design and aims at avoiding magic: you can easily step through Fabric code, its internals won't get in the way.

Here is how you can rewrite the Accelerate BERT example using Fabric:

Import Lightning

Importing lightning as L allows to access all main Fabric \(and PyTorch Lightning\) classes without extra imports.

Set up the dataloader

In order to train a BERT classifier, we load samples from glue-mrpc dataset \(https://huggingface.co/sgugger/glue-mrpc\), tokenize them, and collate them into batches.

Instantiate Fabric

We instantiate the Fabric object, specifying we'll be training in bfloat16 mixed precision for faster training and lower memory usage, and launch processes for multi-GPU training.

Instantiate dataloader, model, and optimizer

We instantiate the dataloader with a batch size of 32, the BERT base cased model from Transformers, and the AdamW optimizer.

Pass model, optimizer and dataloader to Fabric

We provide model, optimizer, and dataloader to Fabric, the returned objects are aware of distributed strategies and mixed precision.

Run the training loop

The training loop is written like in plain PyTorch, with the exception of the call to backward.

Call backward through Fabric

The only deviation from pure PyTorch is fabric.backward\(\) vs loss.backward\(\), so Fabric can manage the computation of the gradients.

`1 2 3 4 5 6 7 8 9 10 11 12 13 14 15 16 17 18 19 20 21 22 23 24 25 26 27 28 29 30 31 32 33 34 35 36 37 38 39 40 41 42 43 44 45 46 47 48 49 50 51 52 53 54 55 56 57 58 ` ` from datasets import load_dataset from torch.optim import AdamW from torch.utils.data import DataLoader  from transformers import AutoModelForSequenceClassification, AutoTokenizer, DataCollatorWithPadding  import lightning as L  def get_dataloader(fabric: L.Fabric, batch_size: int): tokenizer = AutoTokenizer.from_pretrained("bert-base-cased") datasets = load_dataset("glue", "mrpc") def tokenize_function(examples): return tokenizer(examples["sentence1"], examples["sentence2"], truncation=True, max_length=None) with fabric.rank_zero_first(local=True): tokenized_datasets = datasets.map(tokenize_function, batched=True, remove_columns=["idx", "sentence1", "sentence2"], ) tokenized_datasets = tokenized_datasets.rename_column("label", "labels") collator = DataCollatorWithPadding(tokenizer=tokenizer, pad_to_multiple_of=8) train_dataloader = DataLoader( tokenized_datasets["train"], batch_size=batch_size, collate_fn=collator, drop_last=True ) return train_dataloader  def main(): L.seed_everything(42) fabric = L.Fabric(precision="bf16-mixed") fabric.launch() train_dataloader = get_dataloader(fabric, batch_size=32) model = AutoModelForSequenceClassification.from_pretrained("bert-base-cased", return_dict=True) model.train() optimizer = AdamW(params=model.parameters(), lr=1e-5) model, optimizer = fabric.setup(model, optimizer) train_dataloader = fabric.setup_dataloaders(train_dataloader) num_epochs = 3 for epoch in range(num_epochs): for step, batch in enumerate(train_dataloader): optimizer.zero_grad() outputs = model( * *batch) loss = outputs.loss  fabric.print(f"epoch/it {epoch}/{step}, train_loss: {loss}") fabric.backward(loss) optimizer.step() if * *name ** == " * *main * *": main()`

If you paste the code in ` main.py ` , you can just run it with:

`1 ` ` python main.py`

This will work out of the box for Studios, Jobs, and MMT. It will automatically detect available GPUs per machine, as well as the size of the cluster for MMT.

The example will automatically use DDP \(Distributed Data Parallel\) as the distributed strategy. For more advanced strategies, such as FSDP, provide it as the ` strategy ` argument to the ` Fabric ` object:

`1 ` ` fabric = L.Fabric(precision="bf16-mixed", strategy="fsdp")`

Refer to the [documentation](https://lightning.ai/docs/fabric/stable/advanced/model_parallel/fsdp.html) for a full run-down of parallelism strategies in Fabric.

