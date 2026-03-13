# Optimize datasets[](#optimize-datasets)

Whether you have your dataset in a Studio, an S3 connection or the Lightning Drive, for model training, we recommend you optimize the dataset to get at least a 10x speed up in data-loading. Optimizing a dataset ensures GPUs aren't idle waiting for data to load.

## The optimize operator: Compress anything[](#the-optimize-operator-compress-anything)

The optimize operator allows users to apply a function to a list of items and convert the resulting objects into compressed binary files. Then, the StreamingDataset knows how to read those files efficiently.


Select an Image

# Basics[](#basics)

Lightning can efficiently parallelize data optimization on a single machine. For larger tasks, read the next section that covers parallelizing across many machines.

The ` optimize ` operator supports any data structures and types. Serialize whatever you want.

## Toy example 1: Square an integer[](#toy-example-1-square-an-integer)

In the code example below, we have a function applied over a list of integers ranging from 0 to 99. The function takes an integer and returns both the original integer and its square.

`1 2 3 4 5 6 7 8 9 10 11 12 13 ` ` import os from lightning.data import optimize def compress(index): return (index, index ** 2) optimize( fn=compress, inputs=list(range(100)), num_workers=2, output_dir="output_dir", chunk_bytes="64MB", ) `

When checking the output directory, we can find three files: ` chunk-0-0.bin ` , ` chunk-1-0.bin ` and ` index.json ` . The chunk file contains the returned values from the ** ` compress ` ** function converted into their binary format and the ` index.json ` is a tracker of the chunks' content.


Select an Image

You can read those data back using the ` StreamingDataset ` from Lightning Data.

`1 2 3 4 5 ` ` from lightning.data import StreamingDataset dataset = StreamingDataset(input_dir="output_dir") print(dataset[10])`

When executing this code, you can retrieve the 10th element. As expected, you get ` (10, 100) ` .

`1 2 ` ` ⚡ ~ python read.py (10, 100)`

## Toy example 2: Stream images[](#toy-example-2-stream-images)

### 1\. Optimize some images[](#1-optimize-some-images)

`1 2 3 4 5 6 7 8 9 10 11 12 13 14 15 16 17 18 19 20 21 22 ` ` import numpy as np from lightning.data import optimize from PIL import Image # Store random images into the chunks def random_images(index): data = { "index": index, "image": Image.fromarray(np.random.randint(0, 256, (32, 32, 3), np.uint8)), "class": np.random.randint(10), } return data # The data is serialized into bytes and stored into chunks by the optimize operator. if * *name ** == " * *main * *": optimize( fn=random_images, # The function applied over each input. inputs=list(range(1000)), # Provide any inputs. The fn is applied on each item. output_dir="my_dataset", # The directory where the optimized data are stored. num_workers=4, # The number of workers. The inputs are distributed among them. chunk_bytes="64MB" # The maximum number of bytes to write into a chunk. )`

Open a new terminal and run the the ` example_2/write.py ` script.

`1 2 3 4 5 6 7 8 9 10 11 12 13 14 15 16 17 18 19 20 21 22 ` ` ⚡ ~/example_2 python write.py Storing the files under /teamspace/studios/this_studio/example_2/my_dataset Setup started with fast_dev_run=False. Seed set to 42 Setup finished in 0.001 seconds. Found 1000 items to process. Starting 4 workers with 1000 items. Workers are ready ! Starting data processing... Rank 1 inferred the following ` ['int', 'pil', 'int'] ` data format. | 0/1000 [00:00<?, ?it/s] Rank 0 inferred the following ` ['int', 'pil', 'int'] ` data format. Rank 2 inferred the following ` ['int', 'pil', 'int'] ` data format. Rank 3 inferred the following ` ['int', 'pil', 'int'] ` data format. Worker 1 is terminating. Worker 0 is terminating. Worker 2 is terminating. Worker 1 is done. Worker 3 is terminating. Worker 0 is done. Worker 2 is done. Worker 3 is done. Progress: 100%|████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████| 1000/1000 [00:00<00:00, 2311.27it/s] Workers are finished. Finished data processing!`

### 2\. Stream the images[](#2-stream-the-images)

`1 2 3 4 5 6 7 8 9 10 11 12 13 14 15 16 17 ` ` from lightning.data import StreamingDataset from torch.utils.data import DataLoader # Remote path where full dataset is persistently stored input_dir = 'my_dataset' # Create streaming dataset dataset = StreamingDataset(input_dir, shuffle=True) # Check any elements sample = dataset[50] img = sample['image'] cls = sample['class'] print(img, cls) # Create PyTorch DataLoader dataloader = DataLoader(dataset)`

Open a new terminal and run the the ` example_2/read.py ` script.

`1 2 ` ` ⚡ ~/example_2 python read.py <PIL.Image.Image image mode=RGB size=32x32 at 0x7F0006B9B4F0> 4`

## Toy example 3: Tokenize text [](#toy-example-3-tokenize-textandnbsp)

When processing large files like compressed [parquet files](https://en.wikipedia.org/wiki/Apache_Parquet) , you can use python yield to process and store one item at the time to avoid overloading the RAM.

In the code below, we are using ` LlaMa2 tokenizer ` to convert some text contained in parquet files into tokens.

`1 2 3 4 5 6 7 8 9 10 11 12 13 14 15 16 17 18 19 20 21 22 23 24 25 26 27 28 ` ` from pathlib import Path import pyarrow.parquet as pq from lightning.data import optimize from tokenizer import Tokenizer from functools import partial from lightning_cloud.utils.data_connection import add_s3_connection add_s3_connection("tinyllama-template") # 1. Define a function to convert the text within the parquet files into tokens def tokenize_fn(filepath, tokenizer=None): parquet_file = pq.ParquetFile(filepath) # Process per batch to reduce RAM usage for batch in parquet_file.iter_batches(batch_size=8192, columns=["content"]): for text in batch.to_pandas()["content"]: yield tokenizer.encode(text, bos=False, eos=True) # 2. Generate the inputs input_dir = "/teamspace/s3_connections/tinyllama-template" inputs = sorted([f for f in Path(f"{input_dir}/starcoderdata").rglob(" *.parquet")], key=lambda x: x.stat().st_size)[:4] # 3. Store the optimized data wherever you want under "/teamspace/datasets" or "/teamspace/s3_connections" outputs = optimize( fn=partial(tokenize_fn, tokenizer=Tokenizer(f"{input_dir}/checkpoints/Llama-2-7b-hf")), # Note: You can use HF tokenizer or any others inputs=[str(f) for f in inputs], output_dir="output_dir", chunk_size=(2049 * 8012), )`

Then, you can use the ` TokensLoader ` to load the tokens back by specify the ` block_size ` .

`1 2 3 4 5 6 7 8 9 10 11 ` ` import os from lightning.data import StreamingDataset, CombinedStreamingDataset, StreamingDataLoader from lightning.data.streaming.item_loader import TokensLoader from tqdm import tqdm dataset = StreamingDataset(input_dir="output_dir", item_loader=TokensLoader(block_size=2048 + 1), shuffle=True) dataloader = StreamingDataLoader(dataset, batch_size=8, pin_memory=True, num_workers=os.cpu_count()) # Iterate over the data for batch in tqdm(dataloader): pass`

# Parallelize across many machines[](#parallelize-across-many-machines)

Lightning can distribute large workloads across hundreds of machines in parallel. This can reduce the time to complete a data processing task from weeks to minutes by scaling to enough machines.


Select an Image

To apply the ` optimize ` operator across multiple machines, simply provide the ` num_nodes ` and ` machine ` arguments to it as follows:

`1 2 3 4 5 6 7 8 9 10 11 12 13 14 15 16 17 18 19 20 21 22 23 24 25 26 27 28 29 30 ` ` from pathlib import Path import pyarrow.parquet as pq from lightning.data import optimize, Machine from tokenizer import Tokenizer from functools import partial from lightning_cloud.utils.data_connection import add_s3_connection add_s3_connection("tinyllama-template") # 1. Define a function to convert the text within the parquet files into tokens def tokenize_fn(filepath, tokenizer=None): parquet_file = pq.ParquetFile(filepath) # Process per batch to reduce RAM usage for batch in parquet_file.iter_batches(batch_size=8192, columns=["content"]): for text in batch.to_pandas()["content"]: yield tokenizer.encode(text, bos=False, eos=True) # 2. Generate the inputs input_dir = "/teamspace/s3_connections/tinyllama-template" inputs = [str(f) for f in Path(f"{input_dir}/starcoderdata").rglob(" *.parquet")] # 3. Store the optimized data wherever you want under "/teamspace/datasets" or "/teamspace/s3_connections" outputs = optimize( fn=partial(tokenize_fn, tokenizer=Tokenizer(f"{input_dir}/checkpoints/Llama-2-7b-hf")), # Note: You can use HF tokenizer or any others inputs=[str(f) for f in inputs], output_dir="output_dir", chunk_size=(2049 * 8012), num_nodes=32, machine=Machine.DATA_PREP, # You can select between dozens of optimized machines )`


Select an Image

# Streaming Dataset [](#streaming-datasetandnbsp)

We developed ` ` StreamingDataset` ` to optimize training of large datasets stored on the cloud while prioritizing speed, affordability, and scalability.

Specifically crafted for multi-node, distributed training with large models, it enhances accuracy, performance, and user-friendliness. Now, training efficiently is possible regardless of the data's location. Simply stream in the required data when needed.

The ` ` StreamingDataset` ` is compatible with any data type, including images, text, video, and multimodal data and it is a drop-in replacement for your PyTorch [IterableDataset](https://pytorch.org/docs/stable/data.html#torch.utils.data.IterableDataset) class. For example, it is used by [Lit-GPT](https://github.com/Lightning-AI/lit-gpt/blob/main/pretrain/tinyllama.py) to pretrain LLMs.

Finally, the ` StreamingDataset ` is fast\! Check out our [benchmark](https://lightning.ai/lightning-ai/studios/benchmark-cloud-data-loading-libraries) .

Here is an illustration showing how the ` ` StreamingDataset` ` works.


Select an Image

## Benchmarks in the Cloud[](#benchmarks-in-the-cloud)

We benchmarked the Streaming Dataset throughly on Imagenet 1.2 million images in this [Studio](https://lightning.ai/lightning-ai/studios/benchmark-cloud-data-loading-libraries) on an A10G.

Add row above

Add row below

Delete row

Add column to left

Add column to right

Delete column

Mechanism

Images / second

Epoch Time \(in seconds\)

S3 Connection

`320`

`4003.64`

Streaming Dataset

* *` 5800.34 ` **

`220.87`

This is roughly ` 18.12 times faster ` than fetching the images reading one image at the time.

### Multi-GPU / Multi-Node[](#multi-gpu-multi-node)

The ` ** ` StreamingDataset ` ** ` and` ` StreamingDataLoader` ` takes care of everything for you. They automatically make sure each rank receives different batch of data. There is nothing for you to do if you use them.

### Easy data mixing[](#easy-data-mixing)

`1 2 3 4 5 6 7 8 9 10 11 12 13 14 15 16 17 18 19 20 21 22 23 24 25 26 27 28 29 30 ` ` from lightning.data import StreamingDataset, CombinedStreamingDataset from lightning.data.streaming.item_loader import TokensLoader from tqdm import tqdm import os from torch.utils.data import DataLoader train_datasets = [ StreamingDataset( input_dir="s3://tinyllama-template/slimpajama/train/", item_loader=TokensLoader(block_size=2048 + 1), # Optimized loader for tokens used by LLMs  shuffle=True, drop_last=True, ), StreamingDataset( input_dir="s3://tinyllama-template/starcoder/", item_loader=TokensLoader(block_size=2048 + 1), # Optimized loader for tokens used by LLMs  shuffle=True, drop_last=True, ), ] # Mix SlimPajama data and Starcoder data with these proportions: weights = (0.693584, 0.306416) combined_dataset = CombinedStreamingDataset(datasets=train_datasets, seed=42, weights=weights) train_dataloader = DataLoader(combined_dataset, batch_size=8, pin_memory=True, num_workers=os.cpu_count()) # Iterate over the combined datasets for batch in tqdm(train_dataloader): pass`

### Statefulness[](#statefulness)

Lightning Data provides a stateful ` ` StreamingDataLoader` ` . This simplifies resuming training over large datasets.

Note: The ` ` StreamingDataLoader` ` is used by [Lit-GPT](https://github.com/Lightning-AI/lit-gpt/blob/main/pretrain/tinyllama.py) to pretrain LLMs. The statefulness still works when using a mixture of datasets with the` ` CombinedStreamingDataset` ` .

`1 2 3 4 5 6 7 8 9 10 11 12 13 14 15 16 17 18 19 20 21 22 23 24 25 26 27 28 29 30 31 32 33 34 35 36 37 38 39 40 ` ` import os import torch from utils import to_rgb from lightning.data import StreamingDataset, StreamingDataLoader from lightning_cloud.utils.data_connection import add_s3_connection from tqdm import tqdm import torchvision.transforms.v2 as T add_s3_connection("optimized-imagenet-1m") class ImageNetStreamingDataset(StreamingDataset): def * *init * *(self, *args, * *kwargs): self.transform = T.Compose([ T.RandomResizedCrop(224, antialias=True), T.RandomHorizontalFlip(), T.ToDtype(torch.float16, scale=True), ]) super(). * *init * *(*args, * *kwargs) def * *getitem * *(self, index): # Note: If torchvision is installed, we return a tensor image instead of a pil image as it is much faster.  img, class_index = super(). * *getitem * *(index) # <- Whatever you returned from the DatasetOptimizer prepare_item method. return self.transform(to_rgb(img)), int(class_index) dataset = ImageNetStreamingDataset("/teamspace/s3_connections/optimized-imagenet-1m/lightning_data_imagenet/train", shuffle=True) dataloader = StreamingDataLoader(dataset, num_workers=os.cpu_count(), batch_size=64) # Restore the dataLoader state if it exists if os.path.isfile("dataloader_state.pt"): state_dict = torch.load("dataloader_state.pt") dataloader.load_state_dict(state_dict) # Iterate over the data for batch_idx, batch in tqdm(enumerate(dataloader), total=len(dataloader)): # Store the state every 100 batches if batch_idx % 100 == 0: torch.save(dataloader.state_dict(), "dataloader_state.pt")`

### Profiling[](#profiling)

The ` ` StreamingDataLoader` ` supports profiling your data loading. Simply use the` ` profile\_batches` ` argument as follows:

`1 2 3 4 5 6 7 8 9 10 11 12 13 14 15 16 17 18 19 20 21 22 23 24 25 26 27 28 29 30 31 32 ` ` import os import torch from utils import to_rgb from lightning.data import StreamingDataset, StreamingDataLoader from lightning_cloud.utils.data_connection import add_s3_connection from tqdm import tqdm import torchvision.transforms.v2 as T add_s3_connection("optimized-imagenet-1m") class ImageNetStreamingDataset(StreamingDataset): def * *init * *(self, *args, * *kwargs): self.transform = T.Compose([ T.RandomResizedCrop(224, antialias=True), T.RandomHorizontalFlip(), T.ToDtype(torch.float16, scale=True), ]) super(). * *init * *(*args, * *kwargs) def * *getitem * *(self, index): # Note: If torchvision is installed, we return a tensor image instead of a pil image as it is much faster.  img, class_index = super(). * *getitem * *(index) # <- Whatever you returned from the DatasetOptimizer prepare_item method. return self.transform(to_rgb(img)), int(class_index) dataset = ImageNetStreamingDataset("/teamspace/s3_connections/optimized-imagenet-1m/lightning_data_imagenet/train", shuffle=True) dataloader = StreamingDataLoader(dataset, num_workers=os.cpu_count(), batch_size=10, profile_batches=5) # Iterate over the data for batch in dataloader: pass`

This generates a Chrome trace called ` ` result.json` ` . You can explore this trace by opening Chrome browser at the ` ` chrome://tracing` ` URL and load the trace inside.

https://pl-bolts-doc-images.s3.us-east-2.amazonaws.com/Docs\_Studios\_MP4/profile.mp4

Visualize the trace inside Chrome tracing viewer.

### Random access[](#random-access)

Access the data you need when you need it.

`1 2 3 4 5 6 7 8 9 10 ` ` from lightning.data import StreamingDataset from lightning_cloud.utils.data_connection import add_s3_connection add_s3_connection("optimized-imagenet-1m") dataset = StreamingDataset("/teamspace/s3_connections/optimized-imagenet-1m/lightning_data_imagenet/train") print(len(dataset)) # display the length of your data print(dataset[42]) # show the 42th element of the dataset`

### Disk usage limits[](#disk-usage-limits)

Limit the size of the cache holding the chunks.

`1 2 3 4 5 6 ` ` from lightning.data import StreamingDataset from lightning_cloud.utils.data_connection import add_s3_connection add_s3_connection("optimized-imagenet-1m") dataset = StreamingDataset("/teamspace/s3_connections/optimized-imagenet-1m/lightning_data_imagenet/train", max_cache_size="10GB")`

# 📚 Real World Studio Templates[](#real-world-studio-templates)

Here are several [Published Studio Templates](https://lightning.ai/lightning-ai/studios) using the ` optimize ` operator. Check them out to learn more.

Add row above

Add row below

Delete row

Add column to left

Add column to right

Delete column

Dataset

Data Type

Studio Link

[LAION-400M](https://laion.ai/blog/laion-400-open-dataset/)

Image & description

[Use or explore LAION-400MILLION dataset](https://lightning.ai/lightning-ai/studios/use-or-explore-laion-400million-dataset)

[Chesapeake Roads Spatial Context](https://github.com/isaaccorley/chesapeakersc)

Image & Mask

[Convert GeoSpatial data to Lightning Streaming](https://lightning.ai/lightning-ai/studios/convert-spatial-data-to-lightning-streaming)

[Imagenet 1M](https://paperswithcode.com/sota/image-classification-on-imagenet?tag_filter=171)

Image & Label

[Benchmark cloud data-loading libraries](https://lightning.ai/lightning-ai/studios/benchmark-cloud-data-loading-libraries)

[SlimPajama](https://huggingface.co/datasets/cerebras/SlimPajama-627B) & [StartCoder](https://huggingface.co/datasets/bigcode/starcoderdata)

Text

[Prepare the TinyLlama 1T token dataset](https://lightning.ai/lightning-ai/studios/prepare-the-tinyllama-1t-token-dataset)

Generated

Parquet Files

[Convert parquets to Lightning Streaming](https://lightning.ai/lightning-ai/studios/convert-parquets-to-lightning-streaming)

