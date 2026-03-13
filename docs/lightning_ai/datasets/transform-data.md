# Transform data[](#transform-data)

Data transformation tasks such as creating embeddings and extracting features can take a long time to perform locally. Cloud processing can become difficult when processing data at scale.

Lightning offers a native ` map ` operator for efficient data transformation at scale.

## Open template[](#open-template)

Open this Studio template to run the examples described here.

# Map operator[](#map-operator)

Use the Map operator to apply a function to a set of files and save the output to a designated folder. The map operator will be called for every input in the list of inputs.


Select an Image

## API[](#api)

### init[](#init)

`1 2 3 ` ` from lightning.data import map map(fn: function, inputs: list, num_workers: int, output_dir: string)`

### Parameters[](#parameters)

  - * *fn * *\( ` function ` \) - A python function that will be called for each item in the inputs.

  - * *inputs * *\( ` list ` \) - A list of inputs to pass to the fn \(function\) argument.

  - * *num\_workers * *\( ` int ` \) - How many workers to use per machine. A good default here is the number of CPU cores.

  - * *output\_dir * *\( ` string ` \) - Directory where the outputs will be saved to. This is normally new files written with the transformed values.

  - * *num\_nodes * *\( ` int ` \) - Number of machines

  - * *machine * *\( ` Machine ` \) - Machine type


## Examples[](#examples)

This section contains synthetic examples that illustrate the concepts of the map operator.

### Toy example 1: Generate files with the square of an integer[](#toy-example-1-generate-files-with-the-square-of-an-integer)

This example generates a file with the square of each input in the inputs list.

`1 2 3 4 5 6 7 8 9 10 11 12 13 14 ` ` import os from lightning.data import map def create_file_with_square(index, output_dir): output_filepath = os.path.join(output_dir, f"{index}.txt") with open(output_filepath, "w") as f: f.write(str(index ** 2)) map( fn=create_file_with_square, inputs=list(range(100)), num_workers=os.cpu_count(), output_dir="./output_dir" )`

Check that the files were written to the output directory:

`1 2 3 4 5 6 ` ` ⚡ ~ ls output_dir 0.txt 13.txt 18.txt 22.txt 27.txt 31.txt 36.txt 40.txt 45.txt 5.txt 54.txt 59.txt 63.txt 68.txt 72.txt 77.txt 81.txt 86.txt 90.txt 95.txt 1.txt 14.txt 19.txt 23.txt 28.txt 32.txt 37.txt 41.txt 46.txt 50.txt 55.txt 6.txt 64.txt 69.txt 73.txt 78.txt 82.txt 87.txt 91.txt 96.txt 10.txt 15.txt 2.txt 24.txt 29.txt 33.txt 38.txt 42.txt 47.txt 51.txt 56.txt 60.txt 65.txt 7.txt 74.txt 79.txt 83.txt 88.txt 92.txt 97.txt 11.txt 16.txt 20.txt 25.txt 3.txt 34.txt 39.txt 43.txt 48.txt 52.txt 57.txt 61.txt 66.txt 70.txt 75.txt 8.txt 84.txt 89.txt 93.txt 98.txt 12.txt 17.txt 21.txt 26.txt 30.txt 35.txt 4.txt 44.txt 49.txt 53.txt 58.txt 62.txt 67.txt 71.txt 76.txt 80.txt 85.txt 9.txt 94.txt 99.txt`

View the content of the * *44.txt ** file \(44 \* 44 = 1936\)

`1 2 ` ` ⚡ ~ cat output_dir/44.txt 1936`

### Toy example 2: Resize images[](#toy-example-2-resize-images)

This example shows how to resize a folder of images.

### 1\. Generate large images[](#1-generate-large-images)

`1 2 3 4 5 6 7 8 9 10 11 12 13 14 ` ` import os from PIL import Image import numpy as np data_dir = "my_large_images" os.makedirs(data_dir, exist_ok=True) for i in range(1000): width = np.random.randint(224, 320) height = np.random.randint(224, 320) image_path = os.path.join(data_dir, f"{i}.JPEG") Image.fromarray( np.random.randint(0, 256, (width, height, 3), np.uint8) ).save(image_path, format="JPEG", quality=90)`

`1 2 ` ` ⚡ ~ cd basics/example_2_resize_images ⚡ ~/basics/example_2_resize_images python 01_generate_images.py`

### 2\. Resize the images locally[](#2-resize-the-images-locally)


Select an Image

`1 2 3 4 5 6 7 8 9 10 11 12 13 14 15 16 17 18 ` ` import os from lightning.data import map from PIL import Image input_dir = "my_large_images" inputs = [os.path.join(input_dir, f) for f in os.listdir(input_dir)] def resize_image(image_path, output_dir): output_image_path = os.path.join(output_dir, os.path.basename(image_path)) Image.open(image_path).resize((224, 224)).save(output_image_path) if * *name ** == " * *main * *": map( fn=resize_image, inputs=inputs, output_dir="my_resized_images", num_workers=os.cpu_count(), )`

Here, the ` map ` operator applies the ` resize_image ` function directly within the local Studio filesystem. You can run it yourself by opening a terminal and running the following commands:

`1 2 3 4 5 6 7 8 9 10 11 12 13 14 15 16 17 18 19 20 21 22 ` ` ⚡ ~/basics/example_2_resize_images python 02_resize_images.py Storing the files under /teamspace/studios/this_studio/getting_started/my_resized_images Setup started with fast_dev_run=False. Seed set to 42 Worker 0 gets 17.2 MB (250 files) Worker 1 gets 17.2 MB (250 files) Worker 2 gets 17.2 MB (250 files) Worker 3 gets 17.2 MB (250 files) Setup finished in 0.089 seconds. Found 1000 items to process. Starting 4 workers with 1000 items. Workers are ready ! Starting data processing... Worker 0 is terminating.██████████████████████████████████████████████████████████████████████████▎ | 571/1000 [00:01<00:01, 289.15it/s] Worker 1 is terminating. Worker 2 is terminating. Worker 0 is done. Worker 1 is done. Worker 2 is done. Worker 3 is terminating. Worker 3 is done. Progress: 100%|█████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████| 1000/1000 [00:02<00:00, 451.83it/s] Workers are finished. Finished data processing!`

### 3\. Resize images from S3 to local[](#3-resize-images-from-s3-to-local)


Select an Image

`1 2 3 4 5 6 7 8 9 10 11 12 13 14 15 16 17 18 19 20 ` ` import os from PIL import Image from lightning_cloud.utils import add_s3_connection from lightning.data import map add_s3_connection("imagenet-1m-template") def resize_image(image_path, output_dir): output_image_path = os.path.join(output_dir, os.path.basename(image_path)) Image.open(image_path).resize((224, 224)).save(output_image_path) input_dir = "/teamspace/s3_connections/imagenet-1m-template/raw/test" inputs = [os.path.join(input_dir, f) for f in os.listdir(input_dir)][:1000] outputs = map( resize_image, inputs, output_dir="imagenet_imaged_resized", num_downloaders=10, )`

In the code above, the ` map ` operator applies the ` resize_image ` function from images stored on S3 and store the resized ones in the local Studio filesystem. You can run it yourself by opening a terminal and running the following commands:

`1 ` ` ⚡ ~/basics/example_2_resize_images python 03_resize_imagenet.py`

### 4\. Resize images from S3 to S3[](#4-resize-images-from-s3-to-s3)


Select an Image

`1 2 3 4 5 6 7 8 9 10 11 12 13 14 15 16 17 18 19 20 21 ` ` import os from PIL import Image from lightning_cloud.utils import add_s3_connection from lightning.data import map add_s3_connection("imagenet-1m-template") def resize_image(image_path, output_dir): output_image_path = os.path.join(output_dir, os.path.basename(image_path)) Image.open(image_path).resize((224, 224)).save(output_image_path) input_dir = "/teamspace/s3_connections/imagenet-1m-template/raw/test" inputs = [os.path.join(input_dir, f) for f in os.listdir(input_dir)][:1000] outputs = map( resize_image, inputs, output_dir="/teamspace/datasets/imagenet_test", num_downloaders=10, num_uploaders=10, )`

In the code above, the ` map ` operator applies the ` resize_image ` function from images stored on S3 and store the resized images back to S3. You can run it yourself by opening a terminal and running the following commands:

`1 ` ` ⚡ ~/basics/example_2_resize_images python 04_resize_imagenet_to_s3.py`

# Parallelize across machines[](#parallelize-across-machines)

The map operator can distribute data processing tasks across many machines. This allows reducing transform tasks that could take weeks into minutes by scaling out to more machines in parallel.


Select an Image

## Map operator \(distributed\)[](#map-operator-distributed)

To apply the map operator across multiple machines, provide the ` num_nodes ` and ` machine ` arguments to it as follows:

`1 2 3 4 5 6 7 8 9 10 11 12 13 14 15 16 ` ` import os from lightning.data import map, Machine def create_file_with_square(index, output_dir): output_filepath = os.path.join(output_dir, f"{index}.txt") with open(output_filepath, "w") as f: f.write(str(index ** 2)) map( fn=create_file_with_square, inputs=list(range(100_000)), num_workers=os.cpu_count(), output_dir="/teamspace/datasets/squared_files" # create a new dataset num_nodes=32, machine=Machine.DATA_PREP, # You can select between dozens of optimized machines )`


Select an Image

## Distributed examples[](#distributed-examples)

### Toy example 1: Resize images on multiple machines[](#toy-example-1andnbspresize-images-on-multiple-machines)

In the code below, we are starting 4 CPU machines to resize all the images. Under the hood, the map operator knows how best to split the work to be done among the workers and machines.

`1 2 3 4 5 6 7 8 9 10 11 12 13 14 15 16 17 18 19 20 21 22 23 ` ` import os from PIL import Image from lightning_cloud.utils import add_s3_connection from lightning.data import map, Machine add_s3_connection("imagenet-1m-template") def resize_image(image_path, output_dir): output_image_path = os.path.join(output_dir, os.path.basename(image_path)) Image.open(image_path).resize((224, 224)).save(output_image_path) input_dir = "/teamspace/s3_connections/imagenet-1m-template/raw/test" inputs = [os.path.join(input_dir, f) for f in os.listdir(input_dir)] outputs = map( resize_image, inputs, output_dir="/teamspace/datasets/imagenet/test", num_downloaders=10, num_uploaders=10, num_nodes=4, machine=Machine.CPU )`

### Toy example 2: Convert images to tar files[](#toy-example-2andnbspconvert-images-to-tar-files)

Any file structure written to the output directory will be persisted. Here is an example where we convert a dataset of images to [tar files](https://en.wikipedia.org/wiki/Tar_\(computing\) ) using the map operator.

`1 2 3 4 5 6 7 8 9 10 11 12 13 14 15 16 17 18 19 20 21 22 23 24 25 26 27 28 29 30 31 32 33 34 35 36 37 38 39 40 41 42 43 44 45 46 ` ` import os, io, time from PIL import Image from lightning_cloud.utils import add_s3_connection from lightning.data import map, Machine from lightning.data.processing.utilities import get_worker_rank import tarfile add_s3_connection("imagenet-1m-template") class Images2Tar: def * *init * *(self): self.files = [] self.counter = 0 def * *call * *(self, image_path, output_dir, is_last): # 1. Write a tar file when there is enough images or when it is the last image for this worker. if len(self.files) >= 1000 or is_last: tar_filepath = os.path.join(output_dir, f"{get_worker_rank()}_{self.counter}.tar.gz") with tarfile.open(tar_filepath, "w:gz") as tar: for (tar_info, fileobj) in self.files: tar.addfile(tar_info, fileobj=fileobj) self.files = [] self.counter += 1 # 2. Open, resize and conver the image to JPEG fileobj = io.BytesIO() Image.open(image_path).resize((224, 224)).save(fileobj, format="JPEG", quality=90) fileobj.seek(0) # 3. Keep track of the tar infos tar_info = tarfile.TarInfo(name=os.path.basename(image_path)) tar_info.mtime=time.time() tar_info.size=len(fileobj.getvalue()) self.files.append([tar_info, fileobj]) input_dir = "/teamspace/s3_connections/imagenet-1m-template/raw/val" inputs = [os.path.join(input_dir, f) for f in os.listdir(input_dir)] outputs = map( Images2Tar(), inputs, output_dir="output_dir", )`

# Pipelines[](#pipelines)

Apply sequential transformations by creating separate files, each with its own map and optimize calls. Make sure the input directory of one is the output of the following one.

All pipeline steps share the same filesystem which dramatically reduces the complexity of distributed data processing tasks.

## Example 1: Single machine[](#example-1-single-machine)

Here is an example pipeline with 3 steps:

  1. Step 1: Download 32k images from LAION 400M

  2. Step 2: Filter NSFW content from the images

  3. Step 3: Generate CLIP embeddings from the images


### Step 1: Download 32k images from LAION400M[](#step-1-download-32k-images-from-laion400m)

`1 2 3 4 5 6 7 8 9 10 11 12 13 14 15 16 17 18 19 20 21 22 23 24 25 26 27 28 29 30 31 32 33 34 35 36 37 38 39 40 41 42 43 44 45 46 47 48 49 50 51 52 53 54 55 56 57 ` ` import os, math, io, concurrent, time, PIL from lightning.data import optimize, Machine from lightning.data.processing.readers import ParquetReader from lightning.data.processing.utilities import make_request, catch import warnings warnings.filterwarnings("ignore") # Section 1: Define the function to download the image from a URL, resize it to 224 and save it as a JPEG. def download_image_and_prepare(row): # Unpack the row image_id, url, text, _, _, image_license, nsfw, similarity = row # Fetch the image from the URL. The timeout avoids waiting too long for the response.  data = make_request(url, timeout=1.5) # Resize the image, convert it to JPEG, and collect the bytes. buff = io.BytesIO() PIL.Image.open(data).convert('RGB').resize((224, 224)).save(buff, quality=80, format='JPEG') # You can implement a better resizing logic buff.seek(0) img = buff.read() # It is good practice to force the data type to avoid collisions.  return [int(image_id), img, str(text), str(image_license), str(nsfw), float(similarity)] # Section 2: Check whether the row from the parquet file is correctly defined. def is_valid(row): try: return int(row[0]) and isinstance(row[2], str) and row[2] and isinstance(row[1], str) and row[1].startswith("http") and isinstance(row[5], str) and isinstance(row[6], str) and not math.isnan(float(row[7])) except: return False # Section 3: Define the class to fetch the image and serialize it back into Lightning Streaming format class ImageFetcher: def * *init * *(self, max_threads=os.cpu_count()): self.thread_pool = concurrent.futures.ThreadPoolExecutor(max_threads) def * *call * *(self, df): for rows in df.iter_batches(batch_size=2048): rows = [row for row in rows.to_pandas().values.tolist() if is_valid(row) is True] futures = [self.thread_pool.submit(catch(download_image_and_prepare), row) for row in rows] for future in concurrent.futures.as_completed(futures): data, err = future.result() if data is None: continue yield data # Section 4: Use optimize to apply the Image Fetcher over the parquet files. optimize( fn=ImageFetcher(max_threads=16), inputs=["/teamspace/studios/this_studio/pipeline/0_32768_data.parquet"], output_dir="pipeline/output_dir_step_1", reader=ParquetReader("pipeline/data", num_rows=256), num_workers=os.cpu_count(), chunk_bytes="64MB", )`

By using the StreamingDataset, we can observe we have collected 25k images, so we had a success rate of 78%. This is pretty good \!

`1 2 3 4 5 6 ` ` from lightning.data import optimize, StreamingDataset dataset = StreamingDataset(input_dir="pipeline/output_dir_step_1") print(f"We have downloaded {len(dataset)} images.") # Out: We have downloaded 25314 images. `

### Step 2: Filter the NSFW content from the images[](#step-2-filter-the-nsfw-content-from-the-images)

`1 2 3 4 5 6 7 8 9 10 11 12 13 14 15 16 17 ` ` from lightning.data import optimize, StreamingDataset dataset = StreamingDataset(input_dir="pipeline/output_dir_step_1") def filter_nsfw(index): item = dataset[index] image_id, img, text, image_license, nsfw, similarity = item # Keep only the items that meet this condition if nsfw != "NSFW": return item optimize( fn=filter_nsfw, inputs=list(range(len(dataset))), output_dir="pipeline/output_dir_step_2", chunk_bytes="64MB", )`

Again, by using the StreamingDataset, we can observe we removed only 400 images.

`1 2 3 4 5 6 ` ` from lightning.data import optimize, StreamingDataset dataset = StreamingDataset(input_dir="pipeline/output_dir_step_2") print(f"We have {len(dataset)} images after filtering NSFW content.") # Out: We have 24871 images after filtering NSFW content. `

### Step 3: Generate embeddings with CLIP model over images \(requires GPU\)[](#step-3-generate-embeddings-with-clip-model-over-images-requires-gpu)

`1 2 3 4 5 6 7 8 9 10 11 12 13 14 15 16 17 18 19 20 21 22 23 24 25 26 27 28 29 30 31 32 33 ` ` from lightning.data import map, StreamingDataset import open_clip, torch from PIL import Image import os from lightning.data.streaming.serializers import JPEGSerializer dataset = StreamingDataset(input_dir="pipeline/output_dir_step_2") class ClipEmbedder: def * *init * *(self): self.model, _, self.preprocess = open_clip.create_model_and_transforms('ViT-B-32', pretrained='laion2b_s34b_b79k') self.dataset = StreamingDataset(input_dir="output_dir_step_2") self.serializer = JPEGSerializer() def * *call * *(self, indexes, output_dir, device): images = torch.stack([self.serializer.deserialize(dataset[index][1]).cuda() for index in indexes]) image = self.preprocess.transforms [-1](images.float() / 255.) self.model = self.model.to(device) with torch.no_grad(), torch.cuda.amp.autocast(): images_features = self.model.encode_image(image) images_features /= images_features.norm(dim=-1, keepdim=True) images_features = torch.split(images_features.cpu(), len(indexes))[0] for index, image_feature in zip(indexes, images_features): torch.save(image_feature, os.path.join(output_dir, f"{index}.pt")) map( fn=ClipEmbedder(), inputs=list(range(len(dataset))), output_dir="pipeline/output_dir_step_3", num_workers=4, batch_size=32, )`

Once finished, we can check the ` pipeline/output_dir_step_3 ` folder and verify all the embeddings are there.

`1 2 3 4 5 6 7 8 9 10 11 ` ` ⚡ ~ ls pipeline/output_dir_step_3 | head -n 10 0.pt 1.pt 10.pt 100.pt 1000.pt 10000.pt 10001.pt 10002.pt 10003.pt 10004.pt`

# Studio templates[](#studio-templates)

Here are several [Published Studio Templates](https://lightning.ai/lightning-ai/studios) using the ` map ` operator. Check them out to learn more.

Add row above

Add row below

Delete row

Add column to left

Add column to right

Delete column

Dataset

Data Type

Studio

[English Wikipedia](https://huggingface.co/datasets/wikipedia)

Text

[Embed English Wikipedia under 5 dollars](https://lightning.ai/lightning-ai/studios/embed-english-wikipedia-under-5-dollars)

Internet Websites

Text

[How to scrape wed data to finetune LLMs](https://lightning.ai/lightning-ai/studios/how-to-scrape-web-data-to-finetune-llms)

