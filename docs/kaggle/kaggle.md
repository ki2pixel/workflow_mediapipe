# [Kaggle: Your Machine Learning and Data Science Community](https://www.kaggle.com) 
 _https://www.kaggle.com_

## Level up with the largest AI & ML community
Join over 29M+ machine learners to share, stress test, and stay up-to-date on all the latest ML techniques and technologies. Discover a huge repository of community-published models, data & code for your next project.
## Who's on Kaggle?
### New and Exciting
The latest events, big announcements, and high-priority news on Kaggle.
## Validate your models with Benchmarks
Introducing Kaggle Benchmarks. Use our open-source SDK to run rigorous evaluations and see how different models stack up.
### Benchmarks
Create and run custom evaluations for LLMs and GenAI at no cost with our Benchmark SDK.
## Tackle your next project with Kaggle
On Kaggle you'll find all the resources and knowledge needed for your next real-world ML project.
665KDatasets
1.7MNotebooks
41,200Models
### Datasets
665K high-quality public datasets. Everything from avocado prices to video game sales.
### Notebooks
1.7M public notebooks and access to a powerful notebook environment with no cost GPUs & TPUs.
[](https://www.kaggle.com/kaggle5daysofai)
Day 1a - From Prompt to Action
Python
106781 upvotes · 918 comments
[](https://www.kaggle.com/polong)
How to use Kaggle Notebooks¶
Python
2234 upvotes · 20 comments
### Models
41,200 pre-trained, ready-to-deploy ML models.
### Learn cutting edge techniques in Kaggle competitions & courses
Kaggle competitions and courses provide a real-world setting to apply what you learn & connect with other ML practitioners.
32,000Competitions
6,000Write-ups
70+ hoursCourses
### Competitions
Build your skills in our competitions, co-hosted by world-class research organizations & companies.
### Solution write-ups
Learn cutting edge ML techniques and what worked and didn't from the top Kaggle competitors.
1st Place Solution · 340 upvotes
[](https://www.kaggle.com/asuilin)
Web Traffic Time Series Forecasting
1st Place Solution · 458 upvotes
[](https://www.kaggle.com/mjahrer)
Porto Seguro’s Safe Driver Prediction
1st Place Solution · 1099 upvotes
[](https://www.kaggle.com/paweljankiewicz)
Mercari Price Suggestion Challenge
1st Place Solution · 249 upvotes
### Courses
Earn a signed certificate and learn new techniques in our no cost, hands-on courses.
#### Build your ML skills in a supportive and helpful community
Kaggle's community is a diverse group of 29 million data scientists, ML engineers & enthusiasts from around the world.
### Who are Kagglers?
Kagglers come from all walks of life: students, seasoned professionals, and distinguished researchers. They use Kaggle to learn data science & ML, stay up-to-date on the latest techniques, and collaborate.
#### A global community
Over 29 million users from over 190 countries are here.
🇬🇧🇧🇷🇦🇪🇨🇱🇸🇦🇯🇵🇵🇪🇪🇬🇨🇦🇧🇪
#### A place to discuss ML
Whether you're a beginner or pro, find answers to your ML questions & connect with ML enthusiasts on Kaggle's forums.

# [Tensor Processing Units (TPUs) Documentation](https://www.kaggle.com/docs/tpu) 
 _https://www.kaggle.com/docs/tpu_

 TPUs are now available on Kaggle, for free. TPUs are hardware accelerators specialized in deep learning tasks. They are supported in Tensorflow 2.1 both through the Keras high-level API and, at a lower level, in models using a custom training loop.
You can use up to 20 hours per week of TPUs and up to 9h at a time in a single session.
This page explains how to: 1) [Enable TPUs in Tensorflow and Keras](#sec1), 2) [adjust the batch size and learning rate](#sec2), 3) [optimize your data pipeline for a fast accelerator](#sec3)
If you'd like to jump straight into a sample, here it is: [Five flowers with Keras and Xception on TPU](https://www.kaggle.com/code/mgorner/five-flowers-with-keras-and-xception-on-tpu)
The following documentation was written for earlier TPU versions that Kaggle no longer supports. For help with newer versions, see [official TPU documentation.](https://docs.cloud.google.com/tpu/docs)
### TPUs in Keras
Once you have flipped the "Accelerator" switch in your notebook to "TPU v3-8", this is how to enable TPU training in Tensorflow Keras:
 
# detect and init the TPU
tpu = tf.distribute.cluster_resolver.TPUClusterResolver()
# instantiate a distribution strategy
tf.tpu.experimental.initialize_tpu_system(tpu)
tpu_strategy = tf.distribute.TPUStrategy(tpu)
# instantiating the model in the strategy scope creates the model on the TPU
with tpu_strategy.scope():
 model = tf.keras.Sequential( … ) # define your model normally
 model.compile( … )
# train model normally
model.fit(training_dataset, epochs=EPOCHS, steps_per_epoch=…)
 
TPUs are network-connected accelerators and you must first locate them on the network. This is what `TPUClusterResolver.connect()` does.
You then instantiate a `TPUStrategy`. This object contains the necessary distributed training code that will work on TPUs with their 8 compute cores (see [hardware section below](#tpuhardware)).
Finally, you use the `TPUStrategy` by instantiating your model in the scope of the strategy. This creates the model on the TPU. Model size is constrained by the TPU RAM only, not by the amount of memory available on the VM running your Python code. Model creation and model training use the usual Keras APIs.
### Batch size, learning rate, steps\_per\_execution
To go fast on a TPU, increase the batch size. The rule of thumb is to use batches of 128 elements per core (ex: batch size of 128\*8=1024 for a TPU with 8 cores). At this size, the 128x128 hardware matrix multipliers of the TPU (see [hardware section below](#tpuhardware)) are most likely to be kept busy. You start seeing interesting speedups from a batch size of 8 per core though. In the sample above, the batch size is scaled with the core count through this line of code:
BATCH\_SIZE = 16 \* tpu\_strategy.num\_replicas\_in\_sync
With a TPUStrategy running on a single TPU v3-8, the core count is 8. This is the hardware available on Kaggle. It could be more on larger configurations called TPU pods available on Google Cloud.
With larger batch sizes, TPUs will be crunching through the training data faster. This is only useful if the larger training batches produce more “training work” and get your model to the desired accuracy faster. That is why the rule of thumb also calls for increasing the learning rate with the batch size. You can start with a proportional increase but additional tuning may be necessary to find the optimal learning rate schedule for a given model and accelerator.
Starting with Tensorflow 2.4, model.compile() accepts a new `steps_per_execution` parameter. This parameter instructs Keras to send multiple batches to the TPU at once. In addition to lowering communications overheads, this gives the XLA compiler the opportunity to optimize TPU hardware utilization across multiple batches. With this option, it is no longer necessary to push batch sizes to very high values to optimize TPU performance. As long as you use batch sizes of at least 8 per core (>=64 for a TPUv3-8) performance should be acceptable. Example:
 model.compile( … ,
 steps\_per\_execution=32)
 
### tf.data.Dataset and TFRecords
Because TPUs are very fast, many models ported to TPU end up with a data bottleneck. The TPU is sitting idle, waiting for data for the most part of each training epoch. TPUs read training data exclusively from GCS (Google Cloud Storage). And GCS can sustain a pretty large throughput if it is continuously streaming from multiple files in parallel. Following a couple of best practices will optimize the throughput:
> For TPU training, organize your data in GCS in a reasonable number (10s to 100s) of reasonably large files (10s to 100s of MB).
With too few files, GCS will not have enough streams to get max throughput. With too many files, time will be wasted accessing each individual file.
Data for TPU training typically comes sharded across the appropriate number of larger files. The usual container format is TFRecords. You can load a dataset from TFRecords files by writing:
＃ On Kaggle you can also use KaggleDatasets().get_gcs_path() to obtain the GCS path of a Kaggle dataset
filenames = tf.io.gfile.glob("gs://flowers-public/tfrecords-jpeg-512x512/*.tfrec") # list files on GCS
dataset = tf.data.TFRecordDataset(filenames)
dataset = dataset.map(...) # TFRecord decoding here...
 
To enable parallel streaming from multiple TFRecord files, modify the code like this:
 AUTO = tf.data.experimental.AUTOTUNE
 ignore\_order = tf.data.Options()
 ignore\_order.experimental\_deterministic = False
 
 ＃ On Kaggle you can also use KaggleDatasets().get_gcs_path() to obtain the GCS path of a Kaggle dataset
 filenames = tf.io.gfile.glob("gs://flowers-public/tfrecords-jpeg-512x512/\*.tfrec") # list files on GCS
 dataset = tf.data.TFRecordDataset(filenames, num\_parallel\_reads=AUTO)
 dataset = dataset.with\_options(ignore\_order)
 dataset = dataset.map(...) ＃ TFRecord decoding here...
 
There are two settings here:
* `num_parallel_reads=AUTO` instructs the API to read from multiple files if available. It figures out how many automatically.
* `experimental_deterministic = False` disables data order enforcement. We will be shuffling the data anyway so order is not important. With this setting the API can use any TFRecord as soon as it is streamed in.
Some details have been omitted from these code snippets so check the sample for the full data pipeline code. In Keras and TensorFlow 2.1, it is also possible to send training data to TPUs as numpy arrays in memory. This works but is not the most efficient way, although for datasets that fit in memory, it can be OK.
### Private Datasets with TPUs
TPUs work with both public Kaggle Datasets as well as private Kaggle Datasets. The only difference is that if you want to use a private Kaggle Dataset then you need to: (1) enable “Google Cloud SDK” in the “Add-ons” menu of the notebook editor; (2) Initialize the TPU and then run the “Google Cloud SDK credentials” code snippet; finally (3) take note of the Google Cloud Storage path that is returned.
 # Step 1: Get the credential from the Cloud SDK
 from kaggle_secrets import UserSecretsClient
 user_secrets = UserSecretsClient()
 user_credential = user_secrets.get_gcloud_credential()
 
 # Step 2: Set the credentials
 user_secrets.set_tensorflow_credential(user_credential)
 # Step 3: Use a familiar call to get the GCS path of the dataset
 from kaggle_datasets import KaggleDatasets
 GCS_DS_PATH = KaggleDatasets().get_gcs_path()	
 
If you are working with a public Kaggle Dataset then only Step #3 is necessary.
### TPU hardware
At approximately 20 inches (50 cm), a TPU v3-8 board is a fairly sizeable piece of hardware. It sports 4 dual-core TPU chips for a total of 8 TPU cores.
Each TPU core has a traditional vector processing part (VPU) as well as dedicated matrix multiplication hardware capable of processing 128x128 matrices. This is the part that specifically accelerates machine learning workloads.
TPUs are equipped with 128GB of high-speed memory allowing larger batches, larger models and also larger training inputs. In the sample above, you can try using 512x512 px input images, also provided in the dataset, and see the TPU v3-8 handle them easily.
### Model saving/loading on TPUs
When loading and saving models TPU models from/to the local disk, the experimental\_io\_device option must be used. The technical explanation is at the end of this section. It can be omitted if writing to GCS because TPUs have direct access to GCS. This option does nothing on GPUs.
##### Saving a TPU model locally
save\_locally = tf.saved\_model.SaveOptions(experimental\_io\_device='/job:localhost')
model.save('./model', options=save\_locally) ＃ saving in Tensorflow's "SavedModel" format
##### Loading a TPU model from local disk
with strategy.scope():
 load\_locally = tf.saved\_model.LoadOptions(experimental\_io\_device='/job:localhost')
 model = tf.keras.models.load\_model('./model', options=load\_locally) ＃ loading in Tensorflow's "SavedModel" format
##### Writing checkpoints locally from a TPU model
save\_locally = tf.saved\_model.SaveOptions(experimental\_io\_device='/job:localhost')
checkpoints\_cb = tf.keras.callbacks.ModelCheckpoint('./checkpoints', options=save\_locally)
model.fit(…, callbacks=\[checkpoints\_cb\])
##### Loading a model from Tensorflow Hub to TPU directly
import tensorflow\_hub as hub
with strategy.scope():
 load\_locally = tf.saved\_model.LoadOptions(experimental\_io\_device='/job:localhost')
 pretrained\_model = hub.KerasLayer('https://tfhub.dev/tensorflow/efficientnet/b6/feature-vector/1', trainable=True, input\_shape=\[512,512,3\], load\_options=load\_locally)
Example in this [EfficientNetB7 Notebook](https://www.kaggle.com/mgornergoogle/efficientnetb7-on-100-flowers#Model).
##### experimental\_io\_device explained
To understand what the experimental\_io\_device='/job:localhost' flag does, some background info is needed first. TPU users will remember that in order to train a model on TPU, you have to instantiate the model in a TPUStrategy scope. Like this:
＃ connect to a TPU and instantiate a distribution strategy
tpu = tf.distribute.cluster_resolver.TPUClusterResolver(tpu='local')
tf.tpu.experimental.initialize_tpu_system(tpu)
tpu_strategy = tf.distribute.TPUStrategy(tpu)
# instantiate the model in the strategy scope
with tpu_strategy.scope():
 model = tf.keras.Sequential( … )
This boilerplate code actually does 2 things:
The strategy scope instructs Tensorflow to instantiate all the variables of the model in the memory of the TPU. The TPUClusterResolver.connect() call automatically enters the TPU device scope which instructs Tensorflow to run Tensorflow operations on the TPU. Now if you call model.save('./model') when you are connected to a TPU, Tensorflow will try to run the save operations on the TPU and since the TPU is a network-connected accelerator that has no access to your local disk, the operation will fail. Notice that saving to GCS will work though. The TPU does have access to GCS.
If you want to save a TPU model to your local disk, you need to run the saving operation on your local machine and that is what the experimental\_io\_device='/job:localhost' flag does.
### TPUs in Code Competitions
Due to technical limitations for certain kinds of code-only competitions we aren’t able to support notebook submissions that run on TPUs, made clear in the competition's rules. But that doesn’t mean you can’t use TPUs to train your models!
A workaround to this restriction is to run your model training in a separate notebook that uses TPUs, and then to save the resulting model. You can then load that model into the notebook you use for your submission and use a GPU to run inference and generate your predictions.
Here’s how that would work in practice:
**Step 1: Save the Model**
 # Save your model to disk using the .save() functionality. Here we save in .h5 format
 # This step will be replaced with an alternative call to save models in Tensorflow 2.3
 model.save('model.h5')
 
**Step 2: Put your model in a dataset**
You can easily create a dataset from the output of your notebook from the dataviewer. For more details, you can see our [Dataset Documentation](https://www.kaggle.com/docs/datasets#creating-a-dataset)
**Step 3: Load your model into inference Notebook**
 # You can now load your model and run inference using a GPU in this notebook.
 # Because this notebook only uses a GPU, you can submit it to competitions
 model = tf.keras.models.load_model('../input/yourDataset/model.h5')
 ### More information and tutorials
### TPU playground competition
We have prepared a dataset of 13,000 images of flowers for you to play with. You can give TPUs a try in this playground competition: [Flower Classification with TPUs](https://www.kaggle.com/c/flower-classification-with-tpus)
For an easy way to begin, check out this tutorial notebook and starter project, a part of our Deep Learning course:
* [Getting Started with Petals to the Metal](https://www.kaggle.com/ryanholbrook/create-your-first-submission)
* [Starter Project: Create Your First Submission](https://www.kaggle.com/kernels/fork/10204702)
### TPUs in PyTorch
Once you have flipped the "Accelerator" switch in your notebook to "TPU v3-8", this is how to enable TPU training in Tensorflow PyTorch:
 # Step 1: Install Torch-XLA (PyTorch with Accelerated Linear Algebra (XLA) support)
 !curl https://raw.githubusercontent.com/pytorch/xla/master/contrib/scripts/env-setup.py -o pytorch-xla-env-setup.py
 !python pytorch-xla-env-setup.py --version nightly --apt-packages libomp5 libopenblas-dev
 # Step 2: Run your PyTorch code
 TPUs (TPU v3-8) have 8 cores, and each core is itself an XLA device. 
 You can run code on a single XLA device, but to take full advantage of 
 the TPU you will want to run your code on all 8 cores simultaneously. 
 For examples that demonstrate how to do this, you can refer to 
 The Ultimate PyTorch TPU Tutorial,
 I Like Clean TPU Training Kernels and I Can Not Lie,
 Super Duper Fast PyTorch TPU Kernel,
 and XLM Roberta Large Pytorch TPU 
You should also note the following when using TPUs with PyTorch:
 #1: Startup Script 
 https://raw.githubusercontent.com/pytorch/xla/master/contrib/scripts/env-setup.py
 #2: Distributed training function mp_fn
 xmp.spawn(_mp_fn, nprocs=8, start_method='fork')
 #3: Instantiate model outside of mp_fn and use MpModelWrapper
 MX = JigsawModel() => MX = xmp.MpModelWrapper(JigsawModel())
 #4: Send model to TPU device
 device = xm.xla_device()
 model = MX.to(device)
 #5: Changes to training loop: send data to device
 ids = ids.to(device, dtype=torch.long)
 token_type_ids = token_type_ids.to(device, dtype=torch.long)
 mask = mask.to(device, dtype=torch.long)
 targets = targets.to(device, dtype=torch.float)
 #6: Printing messages
 xm.master_print
 #7: Loading data
 train_dataset = … # user-defined, can be outside of mp_fn
 # in mp_fn:
 train_sampler = torch.utils.data.distributed.DistributedSampler(train_dataset,
 num_replicas=xm.xrt_world_size(),rank=xm.get_ordinal(), …)
 train_data_loader = torch.utils.data.DataLoader(train_dataset,
 sampler=train_sampler, …)
 #8: Training on data
 for epoch in range(EPOCHS):
 para_loader = pl.ParallelLoader(train_data_loader, [device])
 train_fn(para_loader.per_device_loader(device), …)
 #9: Results from TPU
 xm.mesh_reduce
 #10: Model save / restore (memory-optimized)
 import torch_xla.utils.serialization as xser
 xser.save(model.state_dict(), f"model.bin", master_only=True)
 model.load_state_dict(xser.load(f"model.bin"))
 #11: Model save / restore (PyTorch standard)
 torch_xla.core.xla_model.save
 torch.load(...)
 #12: Out of memory datasets:
 Can be loaded from localhost
 Of loaded from GCS in TFRecord format, a TFRecords PyTorch loader exists

# [Efficient GPU Usage Tips Documentation](https://www.kaggle.com/docs/efficient-gpu-usage) 
 _https://www.kaggle.com/docs/efficient-gpu-usage_

Kaggle provides free access to NVIDIA TESLA P100 GPUs. These GPUs are useful for training deep learning models, though they do not accelerate most other workflows (i.e. libraries like pandas and scikit-learn do not benefit from access to GPUs).
You can use up to a quota limit per week of GPU. The quota resets weekly and is 30 hours or sometimes higher depending on demand and resources
Here are some tips and tricks to get the most of your GPU usage on Kaggle. In general, your most helpful levers will be:
* Only turn on the GPU if you plan on using the GPU. GPUs are only helpful if you are using code that takes advantage of GPU-accelerated libraries (e.g. TensorFlow, PyTorch, etc).
* Actively monitor and manage your GPU usage
* Kaggle has tools for monitoring GPU usage in the settings menu of the Notebooks editor, at the top of the page at kaggle.com/notebooks, on your profile page, and in the session management window.
* Avoid using batch sessions (the commit button) to save or checkpoint your progress. Batch sessions (commits) run all of the code from top to bottom. This is less efficient than simply downloading the .ipynb file from the Notebook editor.
* Cancel unnecessary batch sessions
* The same Notebook can have multiple concurrent batch sessions if you press the commit button prior to completing the first commit. If your latest code has been updated as compared to your previous code, it is likely better for you to cancel that first commit and leave only the 2nd commit running.
* Stop interactive sessions prior to closing the window. Interactive sessions remain active until they reach the 60 minute idle timeout limit. If you stop the session prior to closing your window it can save you up to 60 minutes of compute.
* You can use the Active Events window in the lower left hand corner of your screen to manage your active sessions including stopping unused interactive sessions. [Learn more about Active Events here](https://www.kaggle.com/product-feedback/193925).
* Consider using the Kaggle-API to avoid interactive sessions entirely. With the Kaggle API you can push a new version of your notebook without ever opening up an interactive session in the Notebook editor.
We hope help you get the most from our free GPU compute. Happy Kaggling!

# [Organizations Documentation](https://www.kaggle.com/docs/organizations) 
 _https://www.kaggle.com/docs/organizations_

* * *
### Overview
Anyone can create an organization profile on Kaggle. Organization profiles allow anyone in the community to find your organization's datasets, models, and competitions in one place.
Before creating an organization, it's helpful to understand how organization profiles work.
* * *
### How do organization profiles work
#### What are organizations for?
Organization profiles are a "landing page" for your organization's published competitions, models, and datasets. For example, it gives you an easy way to share (and other users to find) all of the datasets and models that your team has published with a single link.
#### What are organizations NOT for?
Organizations are not meant to be used as a tool for collaboration with a group of people. You should use [Kaggle groups](https://www.kaggle.com/groups) for this purpose.
Note: While all members of an organization can create competitions, datasets, and models as an organization, this does not give other members of the organization the ability to manage that content (edit, delete, update, or view private resources). Read more about organization permissions below.
#### Who should create and use organization profiles?
For research labs, whether part of a university or industry corporation, organization profiles provide a way to organize the models and datasets your team has published in one place. For large companies, an organization profile will display all of the competitions you've hosted.
For professors, we recommend using a [Kaggle group](https://www.kaggle.com/groups) to make it easier to see and manage datasets, notebooks and models you share in your classes.
* * *
### Creating a new organization profile
#### Creation
Anyone with a Kaggle account can request the creation of an organization profile. To start the process, sign in to your Kaggle account, and then fill out the [new Organization request form](https://www.kaggle.com/contact#/organizations/request-creation).
You'll need to provide the following information:
* **Name**: The name of your organization
* **URL**: You should edit this to something that's short. All links to this organization page will start with this URL, e.g., any datasets or models it owns.
* **Moderation Details**: Some information you share won't appear on your organization profile page, but will be used by our team to review your organization for approval. For example, proof your organization exists outside of Kaggle, your organization's purpose, and your role in the organization.
You'll be able to set the following on your organization profile page after it has been created:
* **Overview**: A "bio" or long description for your organization
* **Tagline**: A short description of your organization
* **Website**: A URL to your organization website
* **Image**: A 400 x 400px image of your organization logo
You'll also be able to change or update most details of your organization freely on the organization profile page, as well as invite members to your organization, and more.
Once you complete the new organization request form, your organization will be reviewed by the Kaggle team for approval, before it's created. Continue to the next section "Review" to learn more about the next steps.
#### Review
Please be patient while your organization is being reviewed by the Kaggle team.
If you have questions about the review process or you would like to appeal a review, please see our contact page: https://www.kaggle.com/contact#/other/issue
#### Approval
Once your organization has been approved, you'll receive an email and/or site notification. You and other members of the organization can now create organization-owned datasets, models, or competitions including making them public. Anyone can also see your organization's profile page.
* * *
### Organization member permissions
#### Abilities of organization members
Organization members can create datasets, models, and competitions under approved organization profiles.
Again, organizations are not currently meant to be used as a tool for collaboration with a group of people. While all members of an organization can create competitions, datasets, and models as an organization, this does not give other members of the organization the ability to manage that content (edit, delete, update, or view private resources).
If you want to share private datasets or models owned by an organization profile, you will need to use Collaboration features.
Similarly, organization members are NOT able to see any unlaunched competitions unless their user is the creator of the competition.
Members will not be able to add new members to an organization unless the organization owner shares the unique invitation link.
#### Abilities of organization admins
Organization admins have the same abilities and permissions as organization members. In addition, they can add and remove members, transfer ownership of the organization to another member, and edit information about the organization (logo, tagline, description, etc.).
* * *
### How to create content as an organization
#### Competitions
Anyone can host a community competition, by clicking the "+Create" button in the upper lefthand corner of any page on Kaggle and selecting "Competition." In order to associate your competition with an organization profile that you are an admin or member of, simply choose your organization from the "Creating As" dropdown.
When a competition is created under an organization profile, the competition will feature your organization's logo and the competition will show up on the "Competitions" tab of your organization's profile page.
When a competition is created under an organization profile, there are NO changes to who can see or manage your competition. That is, other members of the organization cannot see an unlaunched competition and they cannot manage the settings of your competition when it is launched.
#### Datasets and Models
Anyone can publish datasets or models, by clicking the "+Create" button in the upper lefthand corner of any page on Kaggle and selecting "Dataset" or "Model". In order to associate your dataset or model with an organization profile that you are an admin or member of, simply choose your organization from the "Creating As" dropdown.
When a competition is created under an organization profile, the dataset or model will feature your organization's logo and the dataset or model will show up on the "Datasets" or "Models" tab respectively of your organization's profile page.
When a dataset or model is created under an organization profile, other members will be able to see it while it's private. There are NO changes to who can see or manage your datasets or models created under an organization profile. That is, other members of the organization cannot cannot edit, delete, or update the datasets or models unless they are separately added as edit collaborators on the "Settings" tab of the dataset or model.
#### Transferring Resources to an Organization
You can transfer ownership of resources you own to any Organization of which you are a member. Only the owner of the resource can transfer ownership. To transfer ownership, navigate to the resource's detail page and select the "Settings" tab. Scroll down to the "Sharing" section and click "Transfer Ownership", select the Organization you're transferring the resource to and click "Done". Transferring ownership to an organization is not reversible.
* * *
### Model Gating for Organizations
#### What are Gated Models
A gated model is a model on Kaggle that requires users to agree to a specific agreement and potentially provide information before they can access it. This agreement can include terms of use, privacy policy links, and a form for collecting user data.
#### Using Model Gating
To use model gating, start by contacting Kaggle to get permission for your organization and then log in with editor permissions for your model. Enable model gating on the "Settings" tab and customize the gating agreement, specifying review mode (automatic or manual), privacy policy URL, and agreement content in YAML format, which includes title, description, and fields for collecting user information. More details about how to use YAML to create an agreement can be found in [this page](https://www.kaggle.com/model-gating-json-schema).
After enabling gating, manage user consents via UI or API. The API allows listing and reviewing consents, filtering by review status and data expiration. Consents can be approved or rejected, and user data can be downloaded before it expires, adhering to your privacy policy. Users accessing the gated model will be prompted to agree and provide information, with their access status displayed.
#### Gating Publisher API
The base URL for the HTTP endpoints below is [https://www.kaggle.com](https://www.kaggle.com/). The Authorization header uses [HTTP Basic auth](https://en.wikipedia.org/wiki/Basic_access_authentication): `Authorization: Basic <base64-encoded-token>`. The _base64-encoded-token_ token can be created using the username & key generated from [your Kaggle user settings page](https://www.kaggle.com/settings). The username used for authorization also has to be a member of your organization on Kaggle.
Method
URL
Description
Parameters
GET
/api/v1/models/{owner\_slug}/{model\_slug}/user-consents
This endpoint retrieves a list of user consents for a specific gated model under the current agreement, with filtering options by review status and expiration of user request data.
* _owner\_slug_ (in path, required): The model owner slug.
* _model\_slug_ (in path, required): The model slug, e.g., my\_gated\_model.
* _review\_status_\=<null|pending|accepted|rejected>: Filter by review status. Default all (null).
* _is\_user\_request\_data\_expired_\=<null|true|false>: Filter by user request data expiration status. Default all (null).
* _next\_page\_token_: Token for retrieving the next page in paginated results.
POST
/api/v1/models/{owner\_slug}/{model\_slug}/user-consents/review
This endpoint reviews user consent. It requires user\_name and review\_status. Publishers can add notes.
* _owner\_slug_ (in path, required): The model owner slug, this is usually your organization name.
* _model\_slug_ (in path, required): The model slug, e.g., my\_gated\_model.
* _user\_name_ (required): The user to whom the review decision is made. These are usually returned in the response of the List API above.
* _review\_status_ (required)=<pending|accepted|rejected>: The decision on the status of the review.
* _publisher\_notes_: optional notes.

# [Public API Documentation](https://www.kaggle.com/docs/api) 
 _https://www.kaggle.com/docs/api_

### kagglehub & kaggle CLI
Kaggle offers two different ways to interact programmatically with Kaggle:
* [kaggle CLI](https://github.com/Kaggle/kaggle-cli): This is a command-line interface tool for interacting via commands in a terminal or shell script ([Documentation](https://github.com/Kaggle/kaggle-cli/blob/main/docs/README.md)).
* [kagglehub](https://github.com/Kaggle/kagglehub): This is a Python library designed to allow users to interact with Kaggle resource, primarily models, datasets & competitions. It's intended for seamless integration into **Python** ML workflows ([Documentation](https://github.com/Kaggle/kagglehub/blob/main/README.md)).
### Rate Limits
Kaggle uses dynamic rate limiting on both the public API and on calls made while using the kaggle.com website. If you encounter an HTTP 429 error code or a "Too many requests" error, we recommend the following steps:
* Pause and Retry: Often, the most effective solution is to simply wait a few minutes and try your request again later.
* Review Your Logic: It is worth a quick look at your code to ensure no unintended loops or redundant calls are being triggered. This is particularly helpful when making API calls in automated scripts, where a small logic error can inadvertently lead to a high volume of requests.
* Report Platform Issues: If you have investigated your code and believe a bug on the Kaggle site is causing a request to happen more frequently than it should, please report it in the [Product Feedback](https://www.kaggle.com/discussions/product-feedback) forum so we can investigate.
### OAuth 2.0 Provider API
Kaggle implements the OAuth 2.0 Authorization Code flow with PKCE (Proof Key for Code Exchange) for secure authentication. This allows third-party applications to request authorization and access tokens on behalf of Kaggle users.
The API supports:
* **Authorization Code Grant** with PKCE for public clients
* **Refresh Token Grant** for obtaining new access tokens
* **Token Introspection** (RFC 7662) for validating tokens
* **OAuth 2.0 Discovery** via well-known endpoints
#### Quick Start
For public clients (CLI tools, desktop apps, etc.), the typical flow is:
1. Request a pre-configured client ID from the Kaggle team
2. Generate PKCE challenge (code\_verifier and code\_challenge)
3. Redirect user to authorization endpoint with your client details
4. User approves the authorization request on Kaggle
5. Exchange the authorization code for tokens at the token endpoint
6. Use access tokens to call Kaggle APIs
7. Refresh tokens when access tokens expire
#### Discovery Endpoints
Retrieve OAuth 2.0 server metadata including supported endpoints, grant types, and scopes:
 GET https://www.kaggle.com/.well-known/oauth-authorization-server
Retrieve metadata about the protected resource (Kaggle API):
 GET https://www.kaggle.com/.well-known/oauth-protected-resource
#### Client ID Types
Kaggle supports two types of OAuth clients:
Type
Client ID Format
PKCE Required
Redirect URI
Public Client
`<client-name>` (e.g., `gemini-cli`)
Yes
Localhost only
Organization Client
`org:<organization-slug>`
No
HTTPS URLs allowed
To register a new OAuth client, contact the Kaggle team.
##### Step 1: Generate PKCE Challenge
Before starting the authorization flow, generate a PKCE code verifier and challenge:
 import secrets
 import hashlib
 import base64
 
 # Generate a random code_verifier (43-128 characters)
 code_verifier = secrets.token_urlsafe(32)
 
 # Create code_challenge using SHA-256
 code_challenge = base64.urlsafe_b64encode(
 hashlib.sha256(code_verifier.encode()).digest()
 ).decode().rstrip('=')
##### Step 2: Start Authorization Flow
Redirect the user to the authorization endpoint:
 GET https://www.kaggle.com/api/v1/oauth2/authorize
**Query Parameters:**
Parameter
Required
Description
`client_id`
Yes
Your registered client ID
`redirect_uri`
Yes
Must match a registered redirect URI
`scope`
Yes
Space-separated list of scopes
`state`
Yes
Random string (20-128 chars) for CSRF protection
`response_type`
Yes
Must be `"code"`
`response_mode`
Yes
Must be `"query"`
`code_challenge`
Yes\*
Base64URL-encoded SHA-256 hash of code\_verifier
`code_challenge_method`
Yes\*
Must be `"S256"`
_\*Required for public clients_
##### Step 3: User Authorization
The user is redirected to Kaggle's consent screen where they log in (if needed), review the requested permissions, optionally restrict the scopes, and approve or deny the request.
##### Step 4: Receive Authorization Code
After approval, Kaggle redirects back to your `redirect_uri` with the authorization code:
 http://localhost:8080/callback?code=<authorization_code>&state=xyzABC123456789012345
**Important:** Verify that the `state` parameter matches what you sent to prevent CSRF attacks.
##### Step 5: Exchange Code for Tokens
Exchange the authorization code for access and refresh tokens:
 POST https://www.kaggle.com/api/v1/oauth2/token
 Content-Type: application/x-www-form-urlencoded
 
 grant_type=authorization_code&code=<authorization_code>&code_verifier=<your_code_verifier>
**Response:**
 {
 "access_token": "kagat_...",
 "refresh_token": "kagrt_...",
 "token_type": "Bearer",
 "expires_in": 10800,
 "username": "johndoe",
 "user_id": 12345,
 "scope": "datasets.get:* models.get:*"
 }
#### Token Management
##### Refresh Access Token
Access tokens expire after 3 hours. Use the refresh token to obtain new access tokens:
 POST https://www.kaggle.com/api/v1/oauth2/token
 Content-Type: application/x-www-form-urlencoded
 
 grant_type=refresh_token&refresh_token=kagrt_...
##### Token Introspection (RFC 7662)
Validate and inspect tokens:
 POST https://www.kaggle.com/api/v1/oauth2/introspect
 Content-Type: application/x-www-form-urlencoded
 
 token=<access_token_or_refresh_token>
#### Scopes
Scopes control what permissions your application has when acting on behalf of the user. Scopes follow the format: `<permission-or-role>:*`
**Common Permissions:**
Permission
Description
`datasets.get`
Read dataset metadata and files
`datasets.create`
Create new datasets
`datasets.update`
Update existing datasets
`models.get`
Read model metadata
`models.download`
Download model files
`kernels.list`
List notebooks/kernels
`kernels.pull`
Download notebook source
`kernels.push`
Create or update notebooks
`competitions.list`
List competitions
`competitions.submit`
Submit to competitions
**Available Roles** (bundle related permissions):
Role
Description
`datasets.viewer`
Read-only access to datasets
`datasets.editor`
Read and write access to datasets
`models.viewer`
Read-only access to models
`resources.admin`
Full access to all resources
Request multiple scopes by separating them with spaces: `datasets.get:* models.get:* kernels.list:*`
#### Using Access Tokens
Include the access token in API requests using the `Authorization` header:
 curl https://www.kaggle.com/api/v1/datasets/list \
 -H "Authorization: Bearer kagat_..."
#### Error Handling
**Authorization Errors** are returned as query parameters on the redirect URI:
Error Code
Description
`invalid_request`
Missing or invalid parameter
`invalid_client`
Unknown or disabled client
`invalid_scope`
Requested scope not allowed for this client
`access_denied`
User denied authorization
**Token Endpoint Errors** return JSON with HTTP status 400:
Error Code
Description
`invalid_request`
Missing or invalid parameter
`invalid_grant`
Invalid, expired, or revoked authorization code
`invalid_client`
Unknown client ID
#### Security Considerations
* **Always use HTTPS** for non-localhost redirect URIs
* **Validate the state parameter** to prevent CSRF attacks
* **Store refresh tokens securely** - they provide long-lived access
* **Use minimal scopes** - only request permissions your application needs
* **PKCE is mandatory** for public clients to prevent authorization code interception
* **Access tokens expire** after 3 hours - use refresh tokens to obtain new ones

# [Competitions Setup Documentation](https://www.kaggle.com/docs/competitions-setup) 
 _https://www.kaggle.com/docs/competitions-setup_

* * *
### Overview
Anybody can launch a machine learning competition using Kaggle's Community Competitions platform, including educators, researchers, companies, meetup groups, hackathon hosts, or inquisitive individuals! In this guide, you will learn how to set up your own competition, step-by-step.
Before diving in, it's helpful to understand how a Kaggle competition works.
* * *
### How Kaggle competitions work
#### Overview
Every competition has two things, a) a clearly defined problem that participants need to solve using a machine learning model and b) a dataset that’s used both for training and evaluating the effectiveness of these models.
For example, in the [Store Sales – Time Series Forecasting](https://www.kaggle.com/competitions/store-sales-time-series-forecasting) competition, participants must accurately predict how many of each grocery item will sell using a dataset of past product and sales information from a grocery retailer.
Once the competition starts participants can submit their predictions, Kaggle will score them for accuracy, and the team will be placed on a ranked leaderboard. The team at the top of the leaderboard at the deadline wins!
#### Datasets, Submissions & Leaderboards
Every competition’s dataset is split into two smaller datasets.
One of these smaller datasets will be given to participants to train their models, typically named `train.csv`.
The other dataset will be mostly hidden from participants and used by Kaggle for testing and scoring, named `test.csv` and `solution.csv` (`test.csv` is the same as `solution.csv` except that `test.csv` contains the feature values and `solution.csv` contains the ground truth variable(s) – participants will never, ever see `solution.csv` ).
When a participant feels ready to make a submission to the competition, they will use `test.csv` to generate a prediction and upload a CSV file. Kaggle will automatically score the submission for accuracy using the hidden `solution.csv` file.
Most competitions have a maximum number of submissions that a participant can make each day and a final deadline at which point the leaderboard will be frozen.
It’s conceivable that a participant could use the mechanics of a Kaggle competition to overfit a solution - which would be great for winning a competition, but not valuable for a real-world application.
To help prevent this, Kaggle has two leaderboards – the public and private leaderboard. The competition host splits the `solution.csv` dataset into two parts, using one part for the public leaderboard and another part for the private leaderboard. Participants generally will now know which samples are public vs private. The private leaderboard is kept a secret until after the competition deadline and is used as the official leaderboard for determining the final ranking.
* * *
### Create your competition️
To create a new competition, click on the “Create new competition” button at the top of the Kaggle Community landing page.
Then, enter a descriptive title, subtitle and URL for your competition. Be as descriptive and to the point as possible. In our example above, the title “Store Sales - Time Series Forecasting” quickly outlines the type of data, the industry of the dataset, and the type of problem to be solved.
If you want to create a competition with more privacy, you can limit your competition's visibility and restrict who can join on this page.
Visibility: Competitions with their visibility set to public are viewable on Kaggle and appear in Kaggle search results. Competitions with visibility set to private are hidden and only accessible via invitation URLs from the host.
Who Can Join: Competitions access can be set to three levels: anyone, only people with a link and restricted email list. If you select anyone, all Kagglers can join your competition. Selecting only people with a link, will restrict access to those users you provide a special URL. Finally, restricted email list is the most private competition. Only Kagglers with accounts that match the emails or email domains you specify will be able to join. Note: if you select restricted email list, notebooks will be turned off. This provides a way to ensure that any private data that you have in a competition is not accidentally leaked through shared notebooks. You can choose to re-enable notebooks if you choose.
Review and accept our terms of service, then click “Create Competition”.
Your competition listing is now in draft mode. You can take your time to prepare the details before making the competition public.
#### Offering Prizes
Community competition hosts have the option to offer prizes with a total value of up to $10,000 USD.
To set up prizes:
* Enable Prize Awards: When creating a competition, select "Competition will award prizes." Enter the total amount of prize money to be awarded.
* Document Prize Rules: You'll need to specify the number of prizes and the amount for each prize on the Competition Rules and Overview pages. Clearly define the criteria for winning in this section. These sections must be completed to launch the competition.
Adjusting prize amounts:
* Prize amounts can be adjusted or turned off entirely only before launch. After you launch a competition, prize settings are locked. We advise you to double-check your prizes before scheduling, as you won't be able to change them after launch.
* If you are offering a valuable prize that is not cash (eg. gift cards, or valuable objects), please list the monetary value of the prizes in US dollars. The value should not exceed the prize limit of $10,000 USD.
Prize fulfillment:
* Prizes for Community Competitions must be manually awarded and announced. Leaderboards for Community Competitions will not display an "In the money" designation for winning participants. We advise reaching out to winners directly on Kaggle and announcing winners using the Discussions feature.
* When you enable prizes for a competition, you are solely responsible for providing and distributing all prizes, fulfilling all promises and commitments, and for complying with all applicable tax rules related to competition winners. Kaggle does not participate in prize distribution or rule enforcement for Community Competitions.
If you have questions, [contact us](https://admin.kaggle.com/contact#/competitions/hosting).
* * *
### Prepare the dataset
#### Overview
You will typically need to prepare and split your chosen dataset into four CSV files with different purposes and formatting requirements:
* `train.csv` will be given to participants to train their models. It includes the inputs and the ground truth. For example, in the grocery store competition, `train.csv` contains columns of product data and the solution columns – whether or not the product sold. Typically this is roughly 70% of the original dataset.
 
* `test.csv` is given to participants and includes the features of the test set so they can create a submission file with their predictions.
 
* `solution.csv` is always hidden from participants and used by Kaggle’s platform to score submissions. The rows should correspond with those of `test.csv` and typically comprises roughly 30% of the original dataset.
 
* `sample_submission.csv` is a placeholder CSV file with the correct formatting, which helps participants understand the expected submission format for the competition.
 
It's up to you to determine how exactly you'd like to split your dataset into train and test files but it's typically best practice to ensure both train and test have the same type of data represented. Also, most people go with a 70/30 or 75/25 train/test split but it's problem and dataset dependent.
Note: this guide provides instructions for tabular data. Other problem types like image data are possible using similar steps.
##### Implement a unique ID column
Before splitting the dataset, make sure that your dataset has an `Id` column with unique values. The `Id` column is how the scoring system knows which rows of a submission correspond to which rows of the solution. Make sure that the `Id` column is the very first column of your solution file.
##### Prepare the `train.csv` file
Take a large chunk of your dataset, typically 70% and split it into its own dataset named `train.csv`. Be sure not to remove the ground truth column(s) because participants need that information to train their models. Save and set aside for upload later. For example:
 input_feature1,input_feature2,target_feature
 100,52.12,1
 192,203.2,1
 64,-59.1,0
 
##### Prepare the `test.csv` and `solution.csv` files
Take the rest of your dataset and duplicate it to create two identical files.
Then take one file and remove the ground truth column(s) and save it as `test.csv`.
Next, take the other copy and delete all columns except the unique id column and the ground truth column(s). Save it as `solution.csv`.
Your solution file needs to specify which rows will be used for the public leaderboard and which will be used for the private leaderboard. You'll need to add a `Usage` column to your solution file where each row contains one of three values: Public, Private or Ignored. This step is not strictly necessary for competitions that use legacy metrics.
Examples:
 id,input_feature1,input_feature2
 0,93,34.82
 1,104,74.3
 2,89,-12.0
 id,target_feature,Usage
 0,1,Public
 1,0,Private
 2,1,Ignored
 
##### Prepare the `sample_submission.csv` file
Duplicate the `solution.csv` file, delete the `Usage` column, and replace all ground truth values with placeholders that have valid values. Save this as `submission.csv`. This file will be given to users as an example of how to format submissions for evaluation. For example:
 id,target_feature
 0,0
 1,0
 2,0
* * *
### Set up scoring
Navigate to the Host tab > Evaluation Metric page in the right side navigation to set up scoring.
##### Designate your scoring metric
Choose the scoring metric you’d like to use for your competition in the drop down menu, or see below for how to write your own metric in Python.
There are many ways to determine “how accurate” a submission may be. In the grocery store competition example, you may want to reward underestimates more than overestimates, or reward predictions exponentially more the closer they get to the ground truth. If you are unfamiliar with the types of common evaluation metrics used in machine learning, we’d encourage you to take a look at the details of common evaluation metrics to find the right fit.
Kaggle provides two types of metrics: Python (tagged with the icon ) and Legacy (no icon). There are a few key differences. The source code for Legacy metrics is not publicly available and they typically have limited documentation. The setup process is also slightly different: Legacy metrics require manually mapping every column. However, Legacy metrics do offer speed advantages in some circumstances.
When a metric is selected, your competition will be tied to the latest version of that metric. If a newer version is later published, you must manually update your competition to use it.
##### Upload the `solution.csv` file
Click on the upload icon to upload your `solution.csv` file.
If you've chosen a Python metric, check that your solution file's format matches that expected by the metric's documentation, or just continue to testing a submission to see if it matches.
If you've chosen a Legacy metric, then after uploading the `solution.csv` file the column headers will auto populate the Solution Mapping table below. Mapping allows our metric code to understand which columns to use for calculations. Choose the correct “Expected Column” values. Note, some evaluation metrics let you score multiple columns simultaneously.
##### Upload the `sample_submission.csv` file and map the verification
Click on the upload icon to upload your `sample_submission.csv` file.
If you've chosen a Legacy metric, then after uploading you'll again need to complete the same process of column mapping for the submission format.
##### Upload data for participants
Click on the Data tab and “Upload first version” button on the bottom of your screen to upload all data that participants can access – `test.csv`, `train.csv` files and `sample_submission.csv` file. Note: you will have additional data files if creating an image/video/etc. competition. Kaggle will process your data and create a versioned dataset, which will also be made accessible via Kaggle notebooks.
* * *
### Creating a New Metric
You can implement a new metric in a Python notebook at [this link](http://www.kaggle.com/code/metrics/new) or from the Host > Evaluation Metric tab on a competition. Metric notebooks can be published and shared, but currently only Kaggle staff can add metrics to the public metric listing. If you think your metric is a good candidate for general use, please make the notebook public and post in the [competition hosting forum](https://www.kaggle.com/discussions/competition-hosting).
Before your metric executes, Kaggle automatically reads the solution and submission file into Pandas dataframes, aligns the solution and submission rows based on a provided id column, and calls a `score()` function. Your metric code needs to define this `score()` function and it must return a single float. Almost all solution files are split into a `Public` and `Private` set by way of a `Usage` column in the file. The `score()` function is called separately for each of these respective sets.
Your `score()` function must satisfy the following constraints:
* Accept the arguments `solution: pd.DataFrame, submission: pd.DataFrame, row_id_column_name: str`, in that order. You can add any other keyword arguments that you need after those three. Any additional keyword arguments are configured on a per-competition basis on the Evaluation Metric page.
 
* All arguments and the return value of score must have type annotations.
 
* Default argument values are encouraged but not required.
 
* `score()` must return a finite float.
 
* `score()` must have a docstring. The docstring will be shown to competition hosts on the evaluation tab after they have selected a metric. We encourage you to include at least the same sections covered in our [example metric's docstring](https://www.kaggle.com/metric/example-metric-code): a general description of the metric, explanations of each of the `score` arguments, references for the metric math, and examples of valid use.
 
* In order to prevent data leaks from the solution file, errors must specify who will see the details. Only errors raised as `ParticipantVisibleError` will be visible to all participants.
 
* Error messages will be truncated to 280 characters.
 
* The scoring runtime is limited to 30 minutes total for the `Public` and `Private` splits combined.
 
* Metric notebooks do not have internet access and can not use accelerators, so your `score()` function must not rely on these notebook features.
 
Once your code is ready, you will also need to define some metadata in the `Metric` section of the notebook sidebar. You must save this metadata separately from the rest of the notebook.
* Name: your metric will use the metric notebook's name. Save the metadata to update the name.
 
* Description: a short (less than 255 characters) description of the metric.
 
* Category: the main use of the metric, such as clustering or regression.
 
* Leaderboard sort order: toggle this to indicate if a higher score is better or worse.
 
* Pass complete submission: Advanced use only. You almost certainly only want to use this if your submission can have a different number of rows than the solution file. When enabled, your metric will receive the entire submission file for both the public and private scoring rounds. Your metric will need to manage matching the solution and submission rows using the row\_id\_column\_name.
 
You will need to use the dedicated `Save` button in the Metric section of the notebook sidebar for this metadata, in addition to the `Save & Validate` button used to save the notebook's source code. When you save your metric, your notebook will first be committed like any other notebook, followed by a series of metric-specific validation checks. This validation step will also re-run any unit test functions and doctests that are [discoverable with Pytest](https://docs.pytest.org/en/7.1.x/explanation/goodpractices.html#conventions-for-python-test-discovery). We strongly encourage you to include test cases, but they are not mandatory.
If the validation step fails, your notebook code will still save, but no new metric version will be created. We recommend reviewing this [example metric](https://www.kaggle.com/metric/example-metric-code) or [metric template](https://www.kaggle.com/code/metric/metric-template/) before you begin coding.
* * *
### Test your competition
#### Sandbox Testing
Once you set up the solution and submission files you can test submissions in the submission sandbox. You will need at least one sample submission that successfully generates a score in order to launch your competition.
Verify that the scoring is working as intended (e.g. a random submission should have a random score, a perfect submission should have a perfect score, etc.). You may have to experiment to understand what is and is not allowed in submission formats, but the system should provide clear error messages in the event something is wrong with a file.
#### Benchmarking a Solution (Optional)
To create a benchmark score for your participants to meet or exceed, check the box next to the submission you’d like to use as a benchmark. You’ll then see that score listed as a benchmark on the leaderboard.
* * *
### Finalize your settings and descriptions
Most of the heavy lifting is now complete for the competition and it's now time to craft all the final details and settings.
First navigate to the Host tab and complete your configuration in the Basic Details, Images and Evaluation Metric pages.
Then click through the Overview, Data, and Rules tabs and make sure all text descriptions are polished and ready for participants.
You can also go to the Launch Checklist page which shows your remaining steps.
#### Score Decimals to Display
The "Score Decimals to Display" setting on the Basic Details page controls how many decimal places are shown in the user interface. We always use full-precision scores for calculations and ranking comparisons, but it can be useful to truncate the displayed scores to make them look cleaner or to prevent leaderboard probing. For example, if participants can see full-precision scores, they could make small changes to their submission and examine the score difference to infer the ground truth of the public test set, or reverse engineer the split between public and private leaderboards.
* * *
### Launch and invite participants
Go to Host > Launch Checklist and confirm that all the boxes are checked green. Once they are, you’re good to go! Buttons allowing you to launch the competition now or schedule launch in the future will appear – choose according to your needs.
You’ll know your competition is live when it says “Competition is active.”
You can invite participants to your competition by sharing the URL at the bottom of the Launch Checklist or Basic Details. This link respects the access settings you specified when creating the competition. If you selected anyone can join, this link will be the competition URL. If you selected only people with a link, anyone with this URL can participate in the competition, so make sure you share the link with the right audience. If you’d like a select group to participate, send the URL via email. If you’d like broad participation, use social media or encourage participants to invite their friends. If you selected restricted email access, the link will only work if the Kaggler's email address appears on the list of restricted emails you specified.
* * *
### FAQs
#### Creating Your Competition
##### Where can I get a dataset for my competition?
We recommend that you source your own, since it’s typically best to use data to which the participants do not have access (to minimize the temptations to cheat).
But, if you don’t don’t mind it being fully accessible by participants (e.g. for a purely educational competition), consider browsing Kaggle’s Datasets platform. It hosts thousands of public datasets and has rich search and filter tools to help you find something that fits your needs. Each dataset should include a data use license, which will indicate if you can use it for your competition.
##### I’m receiving \[an error\]. How can I resolve it?
Start by reading through this setup guide. If you still can’t resolve the issue, try asking other Community Competition hosts in the Kaggle forums.
##### I want to run the same competition again. Do I need to start from scratch?
For now, you are not able to clone a past competition. You’ll need to start setup from the beginning.
##### Who can see my competition?
It depends on the privacy setting that you chose. Kaggle has 2 privacy settings – public and limited. Public means that your competition will be listed and discoverable on kaggle.com. Limited means that only people with the provided URL can view and join the competition.
##### Where can I find the invitation link?
If you selected Public, you can share your competition from your browser tab – anyone can see the competition. If your competition is set to Limited privacy, visit your competition > Host > Privacy > URL for Sharing (if you’ve selected Limited).
##### How do I contact support?
Unfortunately, we aren’t able to provide hands-on support for setting up or troubleshooting your competition. But, if you are experiencing an issue that you believe is affecting the entire platform, please contact us. We also encourage connecting with other community competition host on Kaggle’s forum.
##### Can I offer a prize for a Community Competition?
Community Competitions can offer a total prize pool of up to $10,000 USD. Competition hosts are solely responsible for providing and distributing all prizes, fulfilling all promises and commitments made, including the full amount of the prizes committed at competition launch, and for complying with all applicable tax rules related to competition winners. Hosts are also solely responsible for facilitating delivery of all prizes to the winner(s), including tax matters and all data privacy considerations and regulations related to receiving taxpayer information or otherwise associated with the your receipt of information from the winner. If you’d like to run a competition with a larger cash prize, please reach out to our Kaggle Competitions Team, who can discuss possible options.
#### During Your Competition
##### Can I invalidate or delete a participant’s submissions?
Yes, go to your competition and navigate to: Host > All Submissions. There you can hide specific submissions.
##### Can I upload a new solution file and rescore the competition?
You can upload a new solution file, but you cannot rescore a competition on your own. Please upload a new solution file and contact support. An administrator can rescore your competition. Competitors’ new submissions will be scored against the new solution file.
##### I would like to download my participants’ email addresses so I can email them for a new competition. How do I do this?
Due to privacy regulations, you cannot currently download the email addresses of participants.
##### I want to give participants more time to compete, how do I change my competition deadline?
If the competition has already ended, you should set up a new competition, as participants will have seen the private leaderboard. If the competition is still active,you can change the deadline by going to: Your competition > Host > Settings >Deadline

# [Login or Register | Kaggle](https://www.kaggle.com/account/login?phase=startRegisterTab&returnUrl=%2Fdocs%2Fcompetitions-setup) 
 _https://www.kaggle.com/account/login?phase=startRegisterTab&returnUrl=%2Fdocs%2Fcompetitions-setup_

Kaggle uses cookies from Google to deliver and enhance the quality of its services and to analyze traffic.
[
Learn more
](https://www.kaggle.com/cookies)
OK, Got it.
## Welcome!
Have an account?
When you link your Google account, Kaggle collects certain information stored in that account that you have configured to make available. By linking your accounts, you authorize Kaggle to access and use your account on the third party service in connection with your use of kaggle.com.
[Contact Us / Support](https://www.kaggle.com/contact)

# [Groups Documentation](https://www.kaggle.com/docs/groups) 
 _https://www.kaggle.com/docs/groups_

* * *
### Overview
Groups allow anyone in the community to easily share Kaggle resources (notebooks, datasets and models) with a group of members. Unlike organizations on Kaggle, groups can never own resources.
### Creating a group
Anyone with a Kaggle account can create a group. Sign in to your Kaggle account, and then click your avatar in the upper right menu and select "Your Groups". You'll see the Groups page. Select "New Group".
You'll need to provide the following information:
* **Name**: The name of your group
* **URL**: Confirm the URL. This will need to be unique — we'll try to base it off of the name of your group, but in case that's already taken, you need to create your own URL.
* **Group Description**: The group description will be visible to members who join the group.
You'll be able to invite members on the group "Invite" tab after it has been created.
#### Sending Invites
On the "Invite" tab, you can add members in two ways: via a link and sending an invite on Kaggle.
* **Invite via a link**: When you turn this on, any admin will see a link on the Invite tab that they can share and grant new members access to the group. Anyone that joins via this method will have a **member role**. Anyone with the link can join the group, so avoid sharing it in public forums. Ensure all admins understand the potential security implications.
* **Send invites**: This invitation method allows you to enter in Kaggle user names and set their individual permission levels (**member** or **admin**) . When you click “Send invites”, invited members will receive an email and a notification on Kaggle with a link to the group.
#### Resending invites
If an invited user somehow doesn't receive an invitation or deletes it, admins can resend the invite. They can do this by viewing the group in question and selecting "Pending Members". They then need to select the "More" menu next to the user and select "Resend invitation".
### Group member permissions
Groups are composed of owners, admins and members.
#### Abilities of group members
Group members can share any notebook, dataset or model they own with their groups (more about sharing below).
Members will not be able to add new members to a group unless the owner or admins shares the unique invitation link.
#### Abilities of group admins
Group admins have the same abilities as members to share resources with their groups. In addition, they can add and remove members, edit link sharing, and edit information about the group (name and description).
#### Abilities of group owners
Group owners have the same abilities as admins. In addition, they can transfer ownership of the group to another admin. Only group owners can delete groups.
#### Changing member permissions
Owners and admins can modify member permissions at any time. This will not affect any resources that have been shared with the group.
Owners and admins can also choose to set their permissions to a lower level if they wish. Owners will need to transfer ownership of the group to another admin before doing so.
### Sharing resources
#### Permissions
Sharing works like it does today, on a resource in the Collaborators section, simply search for the name of a group and select the desired permissions (Can View, Can Edit, Can Administrate) to share a resource.
#### Notifications
A notification (email or site) will be sent to members when a resource is shared with the group. To adjust notifications for a group, visit that group's "Settings" tab. To adjust notifications for all Groups visit "Settings" and select "Notifications".
#### Your Work
Shared resources (notebooks, datasets, and models) will appear under Your Work in the section labeled "All of Your Work". You can filter or search this list to find shared items.
### Group privacy
Groups are private and invitation only. Groups do not appear in search or in directories on Kaggle.
**Note:** If a resource was shared with you that was also shared with a group you are not a member of, you'll be able to see the name of the group on the Collaborators section under Settings, but no additional information about the group.
### FAQs
#### How do I transfer group ownership?
To transfer ownership, select the "People" tab in a group. Select a member and then the role dropdown next to their name. In the menu will be an action "Transfer Ownership". This is a permanent action.

# [Checking your browser - reCAPTCHA](https://www.kaggle.com/docs/datasets) 
 _https://www.kaggle.com/docs/datasets_

Checking your browser before accessing www.kaggle.com ...
Click [here](https://www.google.com/recaptcha/challengepage/#) if you are not automatically redirected after 5 seconds.

# [404](https://www.kaggle.com/docs/notebooks) 
 _https://www.kaggle.com/docs/notebooks_

404 Not Found

# [Competitions Documentation](https://www.kaggle.com/docs/competitions) 
 _https://www.kaggle.com/docs/competitions_

* * *
### Types of Competitions
Kaggle Competitions are designed to provide challenges for competitors at all different stages of their machine learning careers. As a result, they are very diverse, with a range of broad types.
#### Featured
Featured competitions are the types of competitions that Kaggle is probably best known for. These are full-scale machine learning challenges which pose difficult, generally commercially-purposed prediction problems. For example, past featured competitions have included:
* [Allstate Claim Prediction Challenge](https://www.kaggle.com/c/allstate-purchase-prediction-challenge) - Use customers’ shopping history to predict which insurance policy they purchase
 
* [Jigsaw Toxic Comment Classification Challenge](https://www.kaggle.com/c/jigsaw-toxic-comment-classification-challenge) - Predict the existence and type of toxic comments on Wikipedia
 
* [Zillow Prize](https://www.kaggle.com/c/zillow-prize-1) - Build a machine learning algorithm that can challenge Zestimates, the Zillow real estate price estimation algorithm
 
Featured competitions attract some of the most formidable experts, and offer prize pools going as high as a million dollars. However, they remain accessible to anyone and everyone. Whether you’re an expert in the field or a complete novice, featured competitions are a valuable opportunity to learn skills and techniques from the very best in the field.
#### Research
Research competitions are another common type of competition on Kaggle. Research competitions feature problems which are more experimental than featured competition problems. For example, some past research competitions have included:
* [Google Landmark Retrieval Challenge](https://www.kaggle.com/c/landmark-retrieval-challenge) - Given an image, can you find all the same landmarks in a dataset?
 
* [Right Whale Recognition](https://www.kaggle.com/c/noaa-right-whale-recognition) - Identify endangered right whales in aerial photographs
 
* [Large Scale Hierarchical Text Classification](https://www.kaggle.com/c/lshtc) - Classify Wikipedia documents into one of ~300,000 categories
 
Research competitions do not usually offer prizes or points due to their experimental nature. But they offer an opportunity to work on problems which may not have a clean or easy solution and which are integral to a specific domain or area in a slightly less competitive environment.
#### Getting Started
Getting Started competitions are the easiest, most approachable competitions on Kaggle. These are semi-permanent competitions that are meant to be used by new users just getting their foot in the door in the field of machine learning. They offer no prizes or points. Because of their long-running nature, Getting Started competitions are perhaps the most heavily tutorialized problems in machine learning - just what a newcomer needs to get started!
* [Digit Recognizer](https://www.kaggle.com/c/digit-recognizer)
 
* [Titanic: Machine Learning from Disaster](https://www.kaggle.com/c/titanic) - Predict survival on the Titanic
 
* [Housing Prices: Advanced Regression Techniques](https://www.kaggle.com/c/house-prices-advanced-regression-techniques)
 
Getting Started competitions have two-month rolling leaderboards. Once a submission is more than two months old, it is automatically invalidated and no longer counts towards the leaderboard. Similarly, your team will drop from the leaderboard if all its submissions are older than two months. This gives new Kagglers the opportunity to see how their scores stack up against a cohort of competitors, rather than many tens of thousands of users. If your team is removed from a Getting Started competition due to the rolling expiry and wishes to rejoin, creating a new submission will cause it to show again on the leaderboard.
Additionally, the [Kaggle Learn](https://www.kaggle.com/learn/overview) platform has several tracks for beginners interested in free hands-on data science learning from pandas to deep learning. Lessons within a track are separated into easily digestible chunks and contain Notebook exercises for you to practise building models and new techniques. You’ll learn all the skills you need to dive into Kaggle Competitions.
#### Playground
Playground competitions are a “for fun” type of Kaggle competition that is one step above Getting Started in difficulty. These are competitions which often provide relatively simple machine learning tasks, and are similarly targeted at newcomers or Kagglers interested in practicing a new type of problem in a lower-stakes setting. Prizes range from kudos to small cash prizes. Some examples of Playground competitions are:
* [Dogs versus Cats](https://www.kaggle.com/c/dogs-vs-cats) - Create an algorithm to distinguish dogs from cats
 
* [Leaf Classification](https://www.kaggle.com/c/leaf-classification) - Can you see the random forest for the leaves?
 
* [New York City Taxi Trip Duration](https://www.kaggle.com/c/nyc-taxi-trip-duration) - Share code and data to improve ride time predictions
 
* * *
### Competition Formats
In addition to the different categories of competitions (e.g., “featured”), there are also a handful of different formats competitions are run in.
#### Simple Competitions
Simple (or “classic”) competitions are those which follow the standard Kaggle format. In a simple competition, users can access the complete datasets at the beginning of the competition, after accepting the competition’s rules. As a competitor you will download the data, build models on it locally or in [Notebooks](https://www.kaggle.com/notebooks), generate a prediction file, then upload your predictions as a submission on Kaggle. By far most competitions on Kaggle follow this format.
One example of a simple competition is the [Porto Seguro Safe Driver Prediction Competition](https://www.kaggle.com/c/porto-seguro-safe-driver-prediction).
#### Two-stage Competitions
In two-stage competitions the challenge is split into two parts: Stage 1 and Stage 2, with the second stage building on the results teams achieved in Stage 1. Stage 2 involves a new test dataset that is released at the start of the stage. Eligibility for Stage 2 typically requires making a submission in Stage 1. In two-stage competitions, it’s especially important to read and understand the competition’s specific rules and timeline.
One example of such a competition is the [Nature Conservancy Fisheries Monitoring Competition](https://www.kaggle.com/c/the-nature-conservancy-fisheries-monitoring).
#### Code Competitions
Some competitions are code competitions. In these competitions all submissions are made from inside of a Kaggle Notebook, and it is not possible to upload submissions to the Competition directly.
These competitions have two attractive features. The competition is more balanced, as all users have the same hardware allowances. And the winning models tend to be far simpler than the winning models in other competitions, as they must be made to run within the compute constraints imposed by the platform.
Code competitions are configured with their own unique constraints on the Notebooks you can submit. These may be restricted by characteristics like: CPU or GPU runtime, ability to use external data, and access to the internet. To learn the constraints you must adhere to, review the Requirements for that specific competition.
Your submission must finish scoring by the submission deadline to be considered eligible. It's not uncommon for submissions made near the deadline to finish processing after the deadline, and thus be ineligible for consideration on the leaderboard.
An example of a code competition is [Quora Insincere Questions Classification](https://www.kaggle.com/c/quora-insincere-questions-classification).
#### Code Competition FAQ
**I'm getting errors when submitting. What should I do?**
1\. Please see our page on [code competition debugging](https://www.kaggle.com/code-competition-debugging) for tips on understanding and preventing submission errors.
1\. First you'll need to write a Notebook which reads the Competition's dataset and makes predictions on the test set. Specifically, have your Notebook write your predictions to a "submission file", which is typically a submission.csv file, though some competitions have special formats. See the competition's Evaluation page, or look for sample\_submission.csv (or similar) in the Data page for more information on the expected name and format of your submission file.
2\. Save a full version of your Notebook by clicking "Save Version" and selecting "Save & Run All". This saves your code, runs it, and creates a version of the code and output. Once your save finishes, navigate to the Viewer page for your new Notebook Version.
3\. In the Notebook Viewer, navigate to the Output section, find and select the submission file you created, and click the "Submit" button.
**Can I upload external data?**
Some competitions allow external data and some do not. If a competition allows external data, you can attach it to your Notebook by adding it as a data source. If a competition does not allow external data, attaching it to your Notebook will deactivate the "Submit" button on the associated saved version.
**What are the compute limits of Notebooks?**
The compute limits of the Notebooks workers are subject to change. You can view the site-wide memory, CPU, runtime limits, and other limits from the editor.
Code competitions come in many shapes and sizes, and will often impose limits specific to a competition. You should view the competition description to understand if these limits are activated and what they are. Example variations include:
\- Specific runtime limits 
\- Specific limits that apply to Notebooks using GPUs 
\- Internet access allowed or disallowed 
\- External data allowed or disallowed 
\- Custom package installs allowed or disallowed 
\- Submission file naming expectations
**How do I team up in a code competition?**
All the competitions setup is the same as normal competitions, except that submissions are only made through Notebooks. To team up, go to the "Team" tab and invite others.
**How will winners be determined?**
In some code competitions, winners will be determined by re-running selected submissions’ associated Notebooks on a private test set.
In such competitions, you will create your models in Notebooks and make submissions based on the test set provided on the Data page. You will make submissions from your Notebook using the above steps and select submissions for final judging from the “My Submissions” page, in the same manner as a regular competition.
Following the competition deadline, your code will be rerun by Kaggle on a private test set that is not provided to you. Your model's score against this private test set will determine your ranking on the private leaderboard and final standing in the competition.
* * *
### Joining a Competition
Kaggle runs a variety of different kinds of competitions, each featuring problems from different domains and having different difficulties. Before you start, navigate to the [Competitions listing](https://www.kaggle.com/competitions). It lists all of the currently active competitions.
Public competitions are viewable on Kaggle and appear in Kaggle search results. Depending on the privacy and access set by the host, some competitions may be unavailble for you to see or join. If a host set a competition's visibility to private, you would only see the competition's details if they shared a unique URL with you.
If you click on a specific Competition in the listing, you will go to the Competition’s homepage.
The first element worth calling out is the Rules tab. This contains the rules that govern your participation in the sponsor’s competition. You must accept the competition’s rules before downloading the data or making any submissions. It’s extremely important to read the rules before you start. This is doubly true if you are a new user. Users who do not abide by the rules may have their submissions invalidated at the end of the competition or banned from the platform. So please make sure to read and understand the rules before choosing to participate.
If anything is unclear or you have a question about participating, the competition’s forums are the perfect place to ask.
The information provided in the Overview tabs will vary from Competition to Competition. Five elements which are almost always included and should be reviewed are the “Description,” “Data”, “Evaluation,” “Timeline,” & “Prizes” sections.
The **description** gives an introduction into the competition’s objective and the sponsor’s goal in hosting it.
The **data** tab is where you can download and learn more about the data used in the competition. You’ll use a training set to train models and a test set for which you’ll need to make your predictions. In most cases, the data or a subset of it is also accessible in Notebooks.
The **evaluation** section describes how to format your submission file and how your submissions will be evaluated. Each competition employs a metric that serves as the objective measure for how competitors are ranked on the leaderboard.
The **timeline** has detailed information on the competition timeline. Most Kaggle Competitions include, at a minimum, two deadlines: a rules acceptance deadline (after which point no new teams can join or merge in the competition), and a submission deadline (after which no new submissions will be accepted). It is very, very important to keep these deadlines in mind.
The **prizes** section provides a breakdown of what prizes will be awarded to the winners, if prizes are relevant. This may come in the form of monetary, swag, or other perks. In addition to prizes, competitions may also award ranking points towards the Kaggle progression system. This is shown on the Overview page.
Ready to join? If the competition allows anyone to join, you should be able to click "Join" and accept the competition's rules. If the competition has restricted access, the host will share a private link with you that allows you to join.
Once you have chosen a competition, read and accepted the rules, and made yourself aware of the competition deadlines, you are ready to submit!
* * *
### Forming a Team
Everyone that competes in a Competition does so as a team. A team is a group of one or more users who collaborate on the competition. Joining a team of other users around the same level as you in machine learning is a great way to learn new things, combine your different approaches, and generally improve your overall score.
It’s important to keep in mind that team size does not affect the limit on how many submissions you may make to a competition per day: whether you are a team of one or a team of five, you will have the same daily submission limit.
When you accept the rules and join a Competition, you automatically do so as part of a new team consisting solely of yourself. You can then adjust your team settings in various ways by visiting the “Team” tab on the Competition page:
You can perform a number of different team-related actions on this tab.
#### Types of Team Memberships
There are two team membership statuses. One person serves as the Team Leader. They are the primary point of contact when we need to communicate with a team, and also have some additional team modification privileges (to be discussed shortly). Every other person in the team is a Member.
If you are the Team Leader you will see a box next to every other team member’s name on the Team page that says “Make Leader”. You may click on this at any time to designate someone else on your team the Team Leader.
#### Changing your Team Name
The team name is distinct from the names of its members, even if the team only consists of a single person (yourself). You can always change your team name to something custom, and other users will see that custom name when they visit the competition leaderboard. Most teams customize their names!
Anyone in the team can modify the team name by visiting the Team tab.
#### Merging Teams
You may invite another team to your team or, reciprocally, accept a merge request from another team. If you propose a merger, the merger can be accepted or rejected by the Team Leader of the other team. If you are proposed a merger, the Team Leader may choose to accept or reject it.
There are some limits on when you can merge teams:
* Most competitions have a team merger deadline: a point in time by which all teams must be finalized. No mergers may occur after this date
 
* Some competitions specify a maximum team size; you will not be able to merge teams whose cumulative number of members exceeds this cap
 
* You will not be able to merge teams whose combined daily submission count exceeds the total submission limit to that date (daily limit x number of days).
 
All of this can be managed through the Team tab.
#### Disbanding a Team
Choose your teammates wisely as only teams that have not made any submissions can be disbanded. This can be done through the Team tab
* * *
### Making a Submission
You will need to submit your model predictions in order to receive a score and a leaderboard position in a competition. How you go about doing so depends on the format of the competition.
Either way, remember that your team is limited to a certain number of submissions per day. This number is five, on average, but varies from competition to competition.
#### Submitting Predictions
##### Submitting by Uploading a File
In a [Simple Competition](#simple-competitions) format, submitting predictions means uploading a set of predictions (known as a “submission file”) to Kaggle.
Any competition which supports this submission style will have “Submit Predictions” and “My Submissions” buttons in the Competition homepage header.
To submit a new prediction use the Submit Prediction button. This will open a modal that will allow you to upload your submission file. We will attempt to score this file, then add it to My Submissions once it is done being processed.
Note that to count, your submission must first pass processing. If your submission fails during the processing step, it will not be counted and not receive a score; nor will it count against your daily submission limit. If you encounter problems with your submission file, your best course of action is to ask for advice on the Competition’s discussion forum.
##### Submitting by Uploading from a Notebook
In a [Code Competition](#notebooks-only-competitions) format, a submission takes the form of a Kaggle Notebook. Notebooks are an interactive in-browser code editing environment; to learn more about them, see the documentation sections on [Notebooks.](https://www.kaggle.com/docs/notebooks)
To build a model, start by initializing a new Notebook with the Competition Dataset as a data source. This is easily done by going to the “Notebooks” tab within a competition’s page and then clicking “New Notebook.” That competition’s dataset will automatically be used as the data source. New Notebooks will default as private but can be toggled to public or shared with individual users (for example, others on your team).
Build your model and test its performance using the interactive editor. Once you are happy with your model, use it to generate a submission file within the Notebook, and write that submission file to disk in the default working directory (/kaggle/working). Then click "Save Version" and select "Save & Run All" to build a new Notebook version using your code.
Once the new Notebook Version is done (it must run top-to-bottom within the Notebooks platform constraints), navigate to the Notebook Viewer page to see the execution results, then find and select your submission file in the Output section, and you should see a “Submit” button to submit it to the Competition.
If you click on the My Submissions tab you will see a list of every submission you have ever made to this competition. You may also use this tab to select which submission file(s) will be considered for the final rankings. Your final score and placement at the end of the competition will be whichever selected submission performed best on the private leaderboard. If you do not select submission(s) for consideration before the competition closes, the platform will automatically select those which performed the best on the public leaderboard, unless otherwise communicated in the competition. Most competitions allow you to select two submissions.
#### Leaderboard
One of the most important aspects of Kaggle Competitions is the Leaderboard. The Competition leaderboard has two parts.
The _Public Leaderboard_ provides publicly visible submission scores based on a representative sample of the test data. This leaderboard is visible throughout the competition.
The _Private Leaderboard_ tracks model performance using the remainder of the test data. The private leaderboard thus has final say on whose models are best, and hence, who the winners and losers of the Competition will be. Which subset of data is calculated on the private leaderboard or a submission’s performance on the private leaderboard is typically not made public.
Which submission's score is displayed on the leaderboard depends on the competition's status:
1. While a competition is active, the score displayed on the public leaderboard is the best score out of all your submissions. The private leaderboard is not displayed during this phase.
2. As noted above, you may _select_ up to two submissions to be considered for the final private leaderboard. Once a competition is completed, the score displayed on the private leaderboard is best score out of the two selected submissions. The score displayed on the public leaderboard is that submission's score on the public test set. Both leaderboards display scores from the same submission.
Some code competitions follow a "future rerun" format, where only the public test set is used during the submission phase and the selected submissions are rerun on the private test set only after the submission phase ends. In this format, contrary to the traditional format, only the private leaderboard is displayed after a competition completes.
Many users watch the public leaderboard closely, as breakthroughs in the competition are announced by score gains in the leaderboard. These jumps in turn motivate other teams working on the competition in search of those advancements. But it’s important to keep the public leaderboard in perspective. It’s very easy to [overfit](https://en.wikipedia.org/wiki/Overfitting) a model, creating something that performs deceptively well on the public leaderboard, but very badly on the private.
In the event of an exact score tie, the tiebreaker is the team which submitted earlier. Kaggle always uses full precision when determining rankings, not just the truncated precision shown on the Leaderboard.
* * *
### Leakage
#### What is Leakage?
Data Leakage is the presence of unexpected additional information in the training data, allowing a model or machine learning algorithm to make unrealistically good predictions.
Leakage is a pervasive challenge in applied machine learning, causing models to over-represent their generalization error and often rendering them useless in the real world. It can be caused by human or mechanical error, and can be intentional or unintentional in both cases.
Some types of data leakage include:
* Leaking test data into the training data
 
* Leaking the correct prediction or ground truth into the test data
 
* Leaking of information from the future into the past
 
* Retaining proxies for removed variables a model is restricted from knowing
 
* Reversing of intentional obfuscation, randomization or anonymization
 
* Inclusion of data not present in the model’s operational environment
 
* Distorting information from samples outside of scope of the model’s intended use
 
* Any of the above present in third party data joined to the training set
 
#### Examples
One concrete example we’ve seen occurred in a dataset used to predict whether a patient had prostate cancer. Hidden among hundreds of variables in the training data was a variable named PROSSURG. It turned out this represented whether the patient had received prostate surgery, an incredibly predictive but out-of-scope value.
The resulting model was highly predictive of whether the patient had prostate cancer but was useless for making predictions on new patients.
This is an extreme example - many more instances of leakage occur in subtle and hard-to-detect ways. An early Kaggle competition, Link Prediction for Social Networks, makes a good case study in this.
There was a sampling error in the script that created that dataset for the competition: a > sign instead of a >= sign meant that, when a candidate edge pair had a certain property, the edge pair was guaranteed to be true. A team exploited this leakage to take second in the competition.
Furthermore, the winning team won not by using the best machine-learned model, but by scraping the underlying true social network and then defeated anonymization of the nodes with a very clever methodology.
Outside of Kaggle, we’ve heard war stories of models with leakage running in production systems for years before the bugs in the data creation or model training scripts were detected.
#### Leakage in Competitions
Leakage is especially challenging in machine learning competitions. In normal situations, leaked information is typically only used accidentally. But in competitions, participants often find and intentionally exploit leakage where it is present.
Participants may also leverage external data sources to provide more information on the ground truth. In fact, “the concept of identifying and harnessing leakage has been openly addressed as one of three key aspects for winning data mining competitions” ([source paper](http://www.cs.umb.edu/~ding/history/470_670_fall_2011/papers/cs670_Tran_PreferredPaper_LeakingInDataMining.pdf)).
Identifying leakage beforehand and correcting for it is an important part of improving the definition of a machine learning problem. Many forms of leakage are subtle and are best detected by trying to extract features and train state-of-the-art models on the problem. This means that there are no guarantees that competitions will launch free of leakage, especially for Research competitions (which have minimal checks on the underlying data prior to launch).
When leakage is found in a competition, there are many ways that we can address it. These may include:
* Let the competition continue as is (especially if the leakage only has a small impact)
 
* Remove the leakage from the set and relaunch the competition
 
* Generate a new test set that does not have the leakage present
 
Updating the competitions isn’t possible in all cases. It would be better for the competition, the participants, and the hosts if leakage became public knowledge when it was discovered. This would help remove leakage as a competitive advantage and give the host more flexibility in addressing the issue.
* * *
### Resources for Getting Started
#### Getting Started
* The Getting Started Competitions are specifically targeted at new users getting their feet wet with Kaggle and/or machine learning:
 
 * Binary classification: [Titanic: Machine Learning from Disaster](https://www.kaggle.com/c/titanic)
 
 * Regression: [House Prices: Advanced Regression Techniques](https://www.kaggle.com/c/house-prices-advanced-regression-techniques)
 
* The [Kaggle Learn](https://www.kaggle.com/learn/overview) platform has several tracks for beginners interested in free hands-on data science learning from pandas to deep learning. Lessons within a track are separated into easily digestible chunks and contain Notebook exercises for you to practise building models and new techniques hands-on. It is a great way to start deep diving into data science and quickly get familiar with the field!
 
* [What Kaggle has learned from almost 2MM machine learning models](https://www.youtube.com/watch?v=oYNKc_u9Os8) on Youtube. This [data.bythebay.io](http://data.bythebay.io/) talk by Kaggle founder Anthony Goldbloom lays out what Kaggle competitions are all about.
 
* [How to (almost) win at Kaggle](https://www.youtube.com/watch?v=JyEm3m7AzkE) on Youtube. In this talk competitor Kiri Nichols summarizes the appeal of Competitions as a data science learner.
 
#### Discussion
* [General Discussion](https://www.kaggle.com/discussion): There are six general site Discussion Forums:
 
* [Kaggle Forum](https://www.kaggle.com/general): Events and topics specific to the Kaggle community
 
* [Getting Started](https://www.kaggle.com/getting-started): The first stop for questions and discussion for new Kagglers
 
* [Product Feedback](https://www.kaggle.com/product-feedback): Tell us what you love, hate, or wish for
 
* [Questions & Answers](https://www.kaggle.com/questions-and-answers): Technical advice from other data scientists
 
* [Datasets](https://www.kaggle.com/data): Requests for and discussion of open data
 
* [Learn](https://www.kaggle.com/learn-forum): Questions, answers, and requests related to [Kaggle Learn courses](https://www.kaggle.com/learn)
 
* Competition Discussion Forums: No matter the competition you are participating in, you can count on plenty of active community members making posts to the forums. If you get stuck on a particular aspect of the problem, Discussions are a great place to ask questions.
 
* Competition Notebooks: Similar to Discussions, Notebooks shared within a competition are an excellent source of Exploratory Data Analyses (EDAs) & basic starter models which can be forked and built upon for applied learning.
 
* The [Kaggle Noobs Slack channel](https://kagglenoobs.slack.com/): This Slack channel is a popular watering hole for general banter among Kaggle ML practitioners from Novice to Grandmaster.
 
#### Techniques
* Public, reproducible code examples in Notebooks are a great way to learn and put to practice new techniques. Search for techniques in [Notebooks](https://www.kaggle.com/notebooks) by tag using the search syntax `tag:classification`. Fork Notebooks to make a copy of the code to modify and experiment with.
 
* The [No Free Hunch](http://blog.kaggle.com/) blog. No Free Hunch is a great way of keeping up with goings-on on Kaggle. Many past Competitions winners have been interviewed about and presented their winning models on No Free Hunch. Here are some examples of past winner’s interviews:
 
* [NOAA Right Whale Identification](http://blog.kaggle.com/2016/01/29/noaa-right-whale-recognition-winners-interview-1st-place-deepsense-io/)
 
* [Instacart Market Basket Analysis, Winner’s Interview: 2nd place, Kazuki Onodera](http://blog.kaggle.com/2017/09/21/instacart-market-basket-analysis-winners-interview-2nd-place-kazuki-onodera/)
 
* [Two Sigma Financial Modeling Code Competition](http://blog.kaggle.com/2017/05/11/two-sigma-financial-modeling-code-competition-5th-place-winners-interview-team-best-fitting-bestfitting-zero-circlecircle/)
 
* Various [tutorials](http://blog.kaggle.com/category/tutorials/) have been published on No Free Hunch:
 
* [An Intuitive Introduction to Generative Adversarial Networks](http://blog.kaggle.com/2018/01/18/an-intuitive-introduction-to-generative-adversarial-networks/)
 
* [Introduction To Neural Networks](http://blog.kaggle.com/2017/11/27/introduction-to-neural-networks/)
 
* [A Kaggle Master Explains Gradient Boosting](http://blog.kaggle.com/2017/01/23/a-kaggle-master-explains-gradient-boosting/)
 
* [A Kaggler’s Guide to Model Stacking in Practice](http://blog.kaggle.com/2016/12/27/a-kagglers-guide-to-model-stacking-in-practice/)
 
* [Marios Michailidis: How to become a Kaggle #1: An introduction to model stacking](https://www.youtube.com/watch?v=9Vk1rXLhG48): In this Data Science Festival talk top Kaggler Marios Michailidis (Kasanova) explains model stacking, a key feature of winning competition models, in great detail.
 
* [Kaggle Grandmaster Panel](https://www.youtube.com/watch?v=bFHRmesTCc0): A panel Q&A from H2O World 2017 featuring some top Kagglers.
 
* [How to Win A Kaggle Competition - Learn From Top Kagglers](https://www.coursera.org/learn/competitive-data-science): This Coursera course, put together by high-ranking Kagglers, going into great detail on the tools and techniques used by winning Competitions models.
 
* * *
### Cheating
Cheating is not taken lightly on Kaggle. We monitor our [compliance account](https://www.kaggle.com/compliance) (the formal channel for reporting cheaters, or appealing a removal for cheating) during competitions. We also spend a considerable amount of time at the close of each competition to review suspicious activity and remove people who have violated the rules from the leaderboard. When we believe we have sufficient evidence, we take action through removal or possibly even an account ban.
We also monitor and investigate moderation reports (plagiarism, voting rings, etc.) throughout the week, and take action as appropriate, which includes removing medals as well as full-out blocking accounts.
If you believe you have evidence that suggests a team violated competition rules, please report it to the Competitions [compliance account](https://www.kaggle.com/compliance) for a thorough investigation.

# [MCP Server Documentation](https://www.kaggle.com/docs/mcp) 
 _https://www.kaggle.com/docs/mcp_

* * *
## Getting Started
To run the remote server, you need to paste the following code block into your client's configuration. The remote server URL is `https://www.kaggle.com/mcp`.
### Configuration Examples
#### Gemini CLI
 gemini mcp add --transport http kaggle https://www.kaggle.com/mcp
 
Alternatively, you can add the following to your `~/.gemini/settings.json` file:
 
 {
 "mcpServers": {
 "kaggle": {
 "httpUrl": "https://www.kaggle.com/mcp"
 }
 }
 }
 
#### Claude Desktop
 
 {
 "mcpServers": {
 "kaggle": {
 "command": "npx",
 "args": [
 "mcp-remote",
 "https://www.kaggle.com/mcp"
 ]
 }
 }
 }
 
#### VS Code (settings.json)
 
 {
 "servers": {
 "kaggle": {
 "url": "https://www.kaggle.com/mcp",
 "type": "http"
 	}
 	},
 }]
 }
 
#### Windsurf
Add the following to your ~/.codeium/mcp\_config.json:
 
 
 {
 "mcpServers": {
 "kaggle": {
 "serverUrl" : "https://www.kaggle.com/mcp"
 }
 }
 }
 
* * *
## Authorization
Some resources, or endpoints require authorization. To unlock full access you can authorize using OAuth 2.0
#### Gemini CLI
Simply run the following command: `/mcp auth kaggle`
#### Other Clients/IDEs
For other clients that do not have a command to initiate auth discovery you can call the `authorize` tool
### Token Authentication
If your client is not OAuth 2.0 compliant, you can also use token authentication.
If you don't already have a token navigate to [Settings](https://www.kaggle.com/settings) > Generate New Token > "Copy". The token should begin with "KGAT"
#### Gemini CLI
 
 "mcpServers": {
 "kaggle": {
 "transport": "http",
 "httpUrl": "https://www.kaggle.com/mcp",
 "headers": {
 "Authorization": "Bearer YOUR_TOKEN"
 }
 }
 },
 
#### Claude Desktop
 
 {
 "mcpServers": {
 "kaggle": {
 "command": "npx",
 "args": [
 "mcp-remote",
 "https://www.kaggle.com/mcp",
 "--header",
 "Authorization: Bearer YOUR_TOKEN"
 ]
 }
 }
 }
 
#### Vscode
 
 "servers": {
 "kaggle": {
 "url": "https://www.kaggle.com/mcp",
 "type": "http",
 "headers" : {
 "authorization": "Bearer YOUR_TOKEN"
 	}
 	}
 }
 
#### Windsurf
 
 {
 "mcpServers": {
 "kaggle": {
 "command": "npx",
 "args": [
 "-y",
 "mcp-remote",
 "https://www.kaggle.com/mcp",
 "--header",
 "Authorization: Bearer YOUR_TOKEN"
 ]
 }
 }
 }
 
* * *
## Tool Definitions
### Notebooks
##### Request: `ApiCancelKernelSessionRequest`
Field
Type
Description
kernel\_session\_id
int32
The ID of the kernel session to cancel.
##### Response: `ApiCancelKernelSessionResponse`
Field
Type
Description
error\_message
string
Optional error message if the cancellation failed.
##### Request: `ApiCreateKernelSessionRequest`
Field
Type
Description
slug
string
The full slug of the kernel to create an interactive session for, in the format \`{username}/{kernel-slug}\`.
language
string
The language that the kernel is written in. One of "python", "r" and "rmarkdown".
kernel\_type
string
The type of kernel. Options are 'notebook' or 'script'.
docker\_image
string
Which docker image to run with.
machine\_shape
string
The machine shape to use for this session.
enable\_internet
bool
Whether or not the kernel should be able to access the internet in this session.
##### Response: `Operation`
This method returns a long-running operation.
##### Request: `ApiDownloadKernelOutputRequest`
Field
Type
Description
owner\_slug
string
The slug of the owner of the kernel.
kernel\_slug
string
The slug of the kernel.
file\_path
string
Relative path to a specific file inside the databundle.
version\_number
int32
The version number of the kernel.
##### Response: `HttpRedirect`
Returns a URL to download the output.
##### Request: `ApiDownloadKernelOutputZipRequest`
Field
Type
Description
kernel\_session\_id
int32
The ID of the kernel session to download the output from.
##### Response: `FileDownload`
Returns a file download object.
##### Request: `ApiGetKernelRequest`
Field
Type
Description
user\_name
string
The username of the owner of the kernel.
kernel\_slug
string
The slug of the kernel.
##### Response: `ApiGetKernelResponse`
Field
Type
Description
metadata
ApiKernelMetadata
Field
Type
id
int32
ref
string
title
string
author
string
slug
string
last\_run\_time
google.protobuf.Timestamp
language
string
kernel\_type
string
is\_private
bool
enable\_gpu
bool
enable\_tpu
bool
enable\_internet
bool
category\_ids
repeated string
dataset\_data\_sources
repeated string
kernel\_data\_sources
repeated string
competition\_data\_sources
repeated string
model\_data\_sources
repeated string
total\_votes
int32
current\_version\_number
int32
docker\_image
string
machine\_shape
string
The metadata of the kernel.
blob
ApiKernelBlob
Field
Type
source
string
language
string
kernel\_type
string
slug
string
The content of the kernel.
##### Request: `ApiGetKernelSessionStatusRequest`
Field
Type
Description
user\_name
string
The username of the owner of the kernel.
kernel\_slug
string
The slug of the kernel.
##### Response: `ApiGetKernelSessionStatusResponse`
Field
Type
Description
status
KernelWorkerStatus
The status of the session. Possible values: QUEUED, RUNNING, COMPLETE, ERROR, CANCEL\_REQUESTED, CANCEL\_ACKNOWLEDGED, NEW\_SCRIPT.
failure\_message
string
Optional failure message.
##### Request: `ApiListKernelFilesRequest`
Field
Type
Description
user\_name
string
The username of the owner of the kernel.
kernel\_slug
string
The slug of the kernel.
page\_size
int32
The number of items to return.
page\_token
string
The page token to use for pagination.
##### Response: `ApiListKernelFilesResponse`
Field
Type
Description
files
repeated ApiListKernelFilesItem
Field
Type
name
string
size
int64
creation\_date
string
The list of files.
next\_page\_token
string
The next page token.
##### Request: `ApiListKernelSessionOutputRequest`
Field
Type
Description
user\_name
string
The username of the owner of the kernel.
kernel\_slug
string
The slug of the kernel.
page\_size
int32
The number of items to return.
page\_token
string
The page token to use for pagination.
##### Response: `ApiListKernelSessionOutputResponse`
Field
Type
Description
files
repeated ApiKernelSessionOutputFile
Field
Type
url
string
file\_name
string
The list of output files.
log
string
The session log.
next\_page\_token
string
The next page token.
##### Request: `ApiSaveKernelRequest`
Field
Type
Description
id
int32
The kernel's unique ID number.
slug
string
The full slug of the kernel to push to.
new\_title
string
The title to be set on the kernel.
text
string
The kernel's source code.
language
string
The language that the kernel is written in. One of "python", "r" and "rmarkdown".
kernel\_type
string
The type of kernel. Cannot be changed once the kernel has been created.
dataset\_data\_sources
repeated string
A list of dataset data sources that the kernel should use.
kernel\_data\_sources
repeated string
A list of kernel data sources that the kernel should use.
competition\_data\_sources
repeated string
A list of competition data sources that the kernel should use.
category\_ids
repeated string
A list of tag IDs to associated with the kernel.
is\_private
bool
Whether or not the kernel should be private.
enable\_gpu
bool
Whether or not the kernel should run on a GPU. DEPRECATED: use \`machine\_shape\` instead.
enable\_tpu
bool
Whether or not the kernel should run on a TPU. DEPRECATED: use \`machine\_shape\` instead.
enable\_internet
bool
Whether or not the kernel should be able to access the internet.
docker\_image\_pinning\_type
string
Which docker image to use for executing new versions going forward.
model\_data\_sources
repeated string
A list of model data sources that the kernel should use.
##### Response: `ApiSaveKernelResponse`
Field
Type
Description
ref
string
The reference of the kernel.
url
string
The URL of the kernel.
version\_number
int32
The new version number of the kernel.
error
string
An error message if the save failed.
invalid\_tags
repeated string
A list of invalid tags.
invalid\_dataset\_sources
repeated string
A list of invalid dataset sources.
invalid\_competition\_sources
repeated string
A list of invalid competition sources.
invalid\_kernel\_sources
repeated string
A list of invalid kernel sources.
invalid\_model\_sources
repeated string
A list of invalid model sources.
kernel\_id
int32
The ID of the kernel.
##### Request: `ApiListKernelsRequest`
Field
Type
Description
competition
string
Display kernels using the specified competition.
dataset
string
Display kernels using the specified dataset.
parent\_kernel
string
Display kernels that have forked the specified kernel.
group
KernelsListViewType
Display your kernels, collaborated, bookmarked or upvoted kernels. Possible values: PROFILE, UPVOTED, EVERYONE, COLLABORATION, FORK, BOOKMARKED, RECENTLY\_VIEWED, PUBLIC\_AND\_USERS\_PRIVATE.
kernel\_type
string
Display kernels of a specific type.
language
string
Display kernels in a specific language. One of "all", "python", "r", "sqlite" and "julia".
output\_type
string
Display kernels with a specific output type. One of "all", "visualization" and "notebook".
search
string
Display kernels matching the specified search terms.
sort\_by
KernelsListSortType
Sort the results. Possible values: HOTNESS, COMMENT\_COUNT, DATE\_CREATED, DATE\_RUN, RELEVANCE, SCORE\_ASCENDING, SCORE\_DESCENDING, VIEW\_COUNT, VOTE\_COUNT.
user
string
Display kernels by a particular user or group.
page
int32
Page number.
page\_size
int32
Page size, i.e., maximum number of results to return.
page\_token
string
The page token to use for pagination.
##### Response: `ApiListKernelsResponse`
Field
Type
Description
kernels
repeated ApiKernelMetadata
Field
Type
id
int32
ref
string
title
string
author
string
slug
string
last\_run\_time
google.protobuf.Timestamp
language
string
kernel\_type
string
is\_private
bool
enable\_gpu
bool
enable\_tpu
bool
enable\_internet
bool
category\_ids
repeated string
dataset\_data\_sources
repeated string
kernel\_data\_sources
repeated string
competition\_data\_sources
repeated string
model\_data\_sources
repeated string
total\_votes
int32
current\_version\_number
int32
docker\_image
string
machine\_shape
string
List of kernels.
next\_page\_token
string
Next page token.
### Benchmarks
##### Request: `CreateBenchmarkTaskFromPromptRequest`
Field
Type
Description
prompt
string
A natural language prompt describing the benchmark task to be created.
##### Response: `CreateBenchmarkTaskFromPromptResponse`
Field
Type
Description
task
BenchmarkTask
Field
Type
id
int32
type
BenchmarkTaskType
The type of the benchmark task. Possible values: BENCHMARK\_TASK\_TYPE\_UNSPECIFIED, BENCHMARK\_TASK\_TYPE\_BENCHMARK.
version
BenchmarkTaskVersion
Field
Type
id
int32
task\_id
int32
version\_number
int32
name
string
description
string
display\_type
BenchmarkLeaderboardDisplayType
definition
string
source\_kernel\_session\_id
int32
aggregation\_type
BenchmarkTaskVersionAggregationType
child\_task\_versions
repeated BenchmarkTaskVersion
parent\_task\_version\_ids
repeated int32
is\_public
bool
owner\_user
kaggle.users.UserAvatar
type
BenchmarkTaskType
permissions
Permissions
update\_time
google.protobuf.Timestamp
definition\_type
BenchmarkTaskDefinitionType
The definition type of the benchmark task. Possible values: BENCHMARK\_TASK\_DEFINITION\_TYPE\_UNSPECIFIED, NOTEBOOK, PROMPTFOO.
owner\_user\_id
int32
owner\_user
kaggle.users.UserAvatar
source\_kernel\_id
int32
slug
string
vote\_count
int32
has\_up\_voted
bool
forum\_id
int32
is\_public
bool
permissions
Permissions
can\_administer
bool
categories
kaggle.tags.TagList
Field
Type
tags
repeated kaggle.tags.Tag
Field
Type
id
int32
name
string
type
kaggle.tags.TagType
The benchmark task that was created.
##### Request: `ApiGetBenchmarkLeaderboardRequest`
Field
Type
Description
owner\_slug
string
The slug of the user or organization that owns the benchmark.
benchmark\_slug
string
The slug of the benchmark.
version\_number
int32
The version number of the benchmark to get the leaderboard for. If not provided, the latest version is used.
##### Response: `ApiBenchmarkLeaderboard`
Field
Type
Description
rows
repeated LeaderboardRow
Field
Type
model\_version\_name
string
model\_version\_slug
string
task\_results
repeated TaskResult
Field
Type
task\_id
int32
score
double
status
string
The rows of the leaderboard.
### Competitions
##### Request: `ApiCreateCodeSubmissionRequest`
Field
Type
Description
competition\_name
string
The name of the competition.
kernel\_owner
string
The username of the owner of the kernel.
kernel\_slug
string
The slug of the kernel.
kernel\_version
int32
The version number of the kernel.
file\_name
string
The name of the file to submit.
submission\_description
string
A description for the submission.
##### Response: `ApiCreateCodeSubmissionResponse`
Field
Type
Description
message
string
An error message if the submission failed.
ref
int32
The ID of the submission.
##### Request: `ApiCreateSubmissionRequest`
Field
Type
Description
competition\_name
string
Competition name.
blob\_file\_tokens
string
Token identifying location of uploaded submission file.
submission\_description
string
Description of competition submission.
##### Response: `ApiCreateSubmissionResponse`
Field
Type
Description
message
string
Error message from InvalidArgument.
ref
int32
The ID of the submission.
##### Request: `ApiDownloadDataFileRequest`
Field
Type
Description
competition\_name
string
Competition name.
file\_name
string
Name of the file to download.
##### Response: `HttpRedirect`
Returns a URL to download the file.
##### Request: `ApiDownloadDataFilesRequest`
Field
Type
Description
competition\_name
string
Competition name.
##### Response: `HttpRedirect`
Returns a URL to download the files.
##### Request: `ApiDownloadLeaderboardRequest`
Field
Type
Description
competition\_name
string
The name of the competition.
##### Response: `FileDownload`
Returns a file download object.
##### Request: `ApiGetCompetitionRequest`
Field
Type
Description
competition\_name
string
The name of the competition.
##### Response: `ApiCompetition`
Field
Type
Description
id
int32
ref
string
title
string
url
string
description
string
organization\_name
string
organization\_ref
string
category
string
reward
string
tags
repeated ApiCategory
Field
Type
ref
string
name
string
description
string
full\_path
string
competition\_count
int32
dataset\_count
int32
script\_count
int32
total\_count
int32
deadline
google.protobuf.Timestamp
kernel\_count
int32
team\_count
int32
user\_has\_entered
bool
user\_rank
int32
merger\_deadline
google.protobuf.Timestamp
new\_entrant\_deadline
google.protobuf.Timestamp
enabled\_date
google.protobuf.Timestamp
max\_daily\_submissions
int32
max\_team\_size
int32
evaluation\_metric
string
awards\_points
bool
is\_kernels\_submissions\_only
bool
submissions\_disabled
bool
thumbnail\_image\_url
string
host\_name
string
##### Request: `ApiGetCompetitionDataFilesSummaryRequest`
Field
Type
Description
competition\_name
string
The name of the competition.
##### Response: `ApiFilesSummary`
##### Request: `ApiGetLeaderboardRequest`
Field
Type
Description
competition\_name
string
Competition name.
override\_public
bool
By default we return the private leaderboard if it's available, otherwise the public LB. This flag lets you override to get public even if private is available.
page\_size
int32
Page size, i.e., maximum number of results to return.
page\_token
string
Page token.
##### Response: `ApiGetLeaderboardResponse`
Field
Type
Description
submissions
repeated ApiLeaderboardSubmission
Field
Type
team\_id
int32
team\_name
string
submission\_date
google.protobuf.Timestamp
score
string
next\_page\_token
string
##### Request: `ApiGetSubmissionRequest`
Field
Type
Description
ref
int32
SubmissionId.
##### Response: `ApiSubmission`
Field
Type
Description
ref
int32
total\_bytes
int64
date
google.protobuf.Timestamp
description
string
error\_description
string
file\_name
string
public\_score
string
private\_score
string
status
SubmissionStatus
Possible values: PUBLIC, PRIVATE, CANCELLED, ERROR, STUCK, COMPLETE, NONE.
submitted\_by
string
submitted\_by\_ref
string
team\_name
string
url
string
##### Request: `ApiListCompetitionsRequest`
Field
Type
Description
group
CompetitionListTab
Filter competitions by a particular group. Possible values: COMPETITION\_LIST\_TAB\_GENERAL, COMPETITION\_LIST\_TAB\_ENTERED, COMPETITION\_LIST\_TAB\_COMMUNITY, COMPETITION\_LIST\_TAB\_HOSTED, COMPETITION\_LIST\_TAB\_UNLAUNCHED, COMPETITION\_LIST\_TAB\_UNLAUNCHED\_COMMUNITY, COMPETITION\_LIST\_TAB\_EVERYTHING.
category
HostSegment
Filter competitions by a particular category. Possible values: HOST\_SEGMENT\_UNSPECIFIED, HOST\_SEGMENT\_FEATURED, HOST\_SEGMENT\_GETTING\_STARTED, HOST\_SEGMENT\_MASTERS, HOST\_SEGMENT\_PLAYGROUND, HOST\_SEGMENT\_RECRUITMENT, HOST\_SEGMENT\_RESEARCH, HOST\_SEGMENT\_COMMUNITY, HOST\_SEGMENT\_ANALYTICS.
sort\_by
CompetitionSortBy
Sort the results. Possible values: COMPETITION\_SORT\_BY\_GROUPED, COMPETITION\_SORT\_BY\_BEST, COMPETITION\_SORT\_BY\_PRIZE, COMPETITION\_SORT\_BY\_EARLIEST\_DEADLINE, COMPETITION\_SORT\_BY\_LATEST\_DEADLINE, COMPETITION\_SORT\_BY\_NUMBER\_OF\_TEAMS, COMPETITION\_SORT\_BY\_RELEVANCE, COMPETITION\_SORT\_BY\_RECENTLY\_CREATED.
search
string
Filter competitions by search terms.
page
int32
Page number.
page\_token
string
Page token.
page\_size
int32
Page size, i.e., maximum number of results to return.
##### Response: `ApiListCompetitionsResponse`
Field
Type
Description
competitions
repeated ApiCompetition
Field
Type
id
int32
ref
string
title
string
url
string
description
string
organization\_name
string
organization\_ref
string
category
string
reward
string
tags
repeated ApiCategory
Field
Type
ref
string
name
string
description
string
full\_path
string
competition\_count
int32
dataset\_count
int32
script\_count
int32
total\_count
int32
deadline
google.protobuf.Timestamp
kernel\_count
int32
team\_count
int32
user\_has\_entered
bool
user\_rank
int32
merger\_deadline
google.protobuf.Timestamp
new\_entrant\_deadline
google.protobuf.Timestamp
enabled\_date
google.protobuf.Timestamp
max\_daily\_submissions
int32
max\_team\_size
int32
evaluation\_metric
string
awards\_points
bool
is\_kernels\_submissions\_only
bool
submissions\_disabled
bool
thumbnail\_image\_url
string
host\_name
string
next\_page\_token
string
##### Request: `ApiListDataFilesRequest`
Field
Type
Description
competition\_name
string
Competition name.
page\_size
int32
Page size, i.e., maximum number of results to return.
page\_token
string
Page token.
##### Response: `ApiListDataFilesResponse`
Field
Type
Description
files
repeated ApiDataFile
Field
Type
ref
string
name
string
description
string
total\_bytes
int64
url
string
creation\_date
google.protobuf.Timestamp
next\_page\_token
string
children\_fetch\_time\_ms
int32
##### Request: `ApiListDataTreeFilesRequest`
Field
Type
Description
competition\_name
string
Competition name.
path
string
The path of the directory to list files from.
page\_size
int32
Page size, i.e., maximum number of results to return.
page\_token
string
Page token.
##### Response: `ApiDirectoryContent`
Field
Type
Description
directories
repeated ApiDirectory
Field
Type
name
string
relative\_url
string
total\_directories
int64
total\_files
int64
total\_children
int64
files
repeated ApiFile
Field
Type
name
string
creation\_date
google.protobuf.Timestamp
total\_bytes
int64
relative\_url
string
description
string
total\_children
int64
total\_directories
int64
total\_files
int64
next\_page\_token
string
##### Request: `ApiListSubmissionsRequest`
Field
Type
Description
competition\_name
string
Competition name.
sort\_by
SubmissionSortBy
Possible values: SUBMISSION\_SORT\_BY\_DATE, SUBMISSION\_SORT\_BY\_NAME, SUBMISSION\_SORT\_BY\_PRIVATE\_SCORE, SUBMISSION\_SORT\_BY\_PUBLIC\_SCORE.
group
SubmissionGroup
Possible values: SUBMISSION\_GROUP\_ALL, SUBMISSION\_GROUP\_SUCCESSFUL, SUBMISSION\_GROUP\_SELECTED.
page
int32
Page number.
page\_token
string
Page token.
page\_size
int32
Page size, i.e., maximum number of results to return.
##### Response: `ApiListSubmissionsResponse`
Field
Type
Description
submissions
repeated ApiSubmission
Field
Type
ref
int32
total\_bytes
int64
date
google.protobuf.Timestamp
description
string
error\_description
string
file\_name
string
public\_score
string
private\_score
string
status
SubmissionStatus
submitted\_by
string
submitted\_by\_ref
string
team\_name
string
url
string
next\_page\_token
string
##### Request: `ApiStartSubmissionUploadRequest`
Field
Type
Description
competition\_name
string
Competition name.
content\_length
int64
The length of the file in bytes.
last\_modified\_epoch\_seconds
int64
The last modified time of the file in epoch seconds.
file\_name
string
Comes from form upload.
##### Response: `ApiStartSubmissionUploadResponse`
### Datasets
##### Request: `ApiCreateDatasetRequest`
Field
Type
Description
id
int32
The ID of the dataset.
owner\_slug
string
The slug of the owner of the dataset.
slug
string
The slug of the dataset.
title
string
The title of the dataset.
license\_name
string
The name of the license.
is\_private
bool
Whether the dataset is private.
files
repeated ApiDatasetNewFile
Field
Type
file\_name
string
content
bytes
content\_type
string
The files to upload to the dataset.
subtitle
string
The subtitle of the dataset.
description
string
The description of the dataset.
category\_ids
repeated string
The category IDs to associate with the dataset.
directories
repeated ApiUploadDirectoryInfo
Field
Type
path
string
files
repeated ApiDatasetNewFile
The directories to upload to the dataset.
##### Response: `ApiCreateDatasetResponse`
##### Request: `ApiCreateDatasetVersionRequest`
Field
Type
Description
owner\_slug
string
The slug of the owner of the dataset.
dataset\_slug
string
The slug of the dataset.
body
ApiCreateDatasetVersionRequestBody
Field
Type
version\_notes
string
delete\_old\_versions
bool
files
repeated ApiDatasetNewFile
Field
Type
file\_name
string
content
bytes
content\_type
string
subtitle
string
description
string
category\_ids
repeated string
directories
repeated kaggle.datasets.ApiUploadDirectoryInfo
Field
Type
path
string
files
repeated ApiDatasetNewFile
The request body.
##### Response: `ApiCreateDatasetResponse`
##### Request: `ApiCreateDatasetVersionByIdRequest`
Field
Type
Description
id
int32
The ID of the dataset.
body
ApiCreateDatasetVersionRequestBody
Field
Type
version\_notes
string
delete\_old\_versions
bool
files
repeated ApiDatasetNewFile
Field
Type
file\_name
string
content
bytes
content\_type
string
subtitle
string
description
string
category\_ids
repeated string
directories
repeated kaggle.datasets.ApiUploadDirectoryInfo
Field
Type
path
string
files
repeated ApiDatasetNewFile
The request body.
##### Response: `ApiCreateDatasetResponse`
##### Request: `ApiDownloadDatasetRequest`
Field
Type
Description
owner\_slug
string
The slug of the owner of the dataset.
dataset\_slug
string
The slug of the dataset.
file\_name
string
The name of the file to download.
dataset\_version\_number
int32
The version number of the dataset.
raw
bool
Whether to download the raw version of the dataset.
hash\_link
string
A hash link to the dataset.
##### Response: `HttpRedirect`
Returns a URL to download the dataset.
##### Request: `ApiGetDatasetRequest`
Field
Type
Description
owner\_slug
string
The slug of the owner of the dataset.
dataset\_slug
string
The slug of the dataset.
##### Response: `ApiDataset`
Field
Type
Description
id
int32
ref
string
subtitle
string
creator\_name
string
creator\_url
string
total\_bytes
int64
url
string
last\_updated
google.protobuf.Timestamp
download\_count
int32
is\_private
bool
is\_featured
bool
license\_name
string
description
string
owner\_name
string
owner\_ref
string
kernel\_count
int32
title
string
topic\_count
int32
view\_count
int32
vote\_count
int32
current\_version\_number
int32
usability\_rating
float
tags
repeated ApiCategory
Field
Type
ref
string
name
string
description
string
full\_path
string
competition\_count
int32
dataset\_count
int32
script\_count
int32
total\_count
int32
files
repeated ApiDatasetFile
Field
Type
ref
string
dataset\_ref
string
owner\_ref
string
name
string
creation\_date
google.protobuf.Timestamp
description
string
file\_type
string
url
string
total\_bytes
int64
columns
repeated ApiDatasetColumn
Field
Type
order
int32
name
string
type
string
original\_type
string
description
string
versions
repeated ApiDatasetVersion
Field
Type
version\_number
int32
creation\_date
google.protobuf.Timestamp
creator\_name
string
creator\_ref
string
version\_notes
string
status
string
thumbnail\_image\_url
string
##### Request: `ApiGetDatasetFilesSummaryRequest`
Field
Type
Description
owner\_slug
string
The slug of the owner of the dataset.
dataset\_slug
string
The slug of the dataset.
dataset\_version\_number
int32
The version number of the dataset.
##### Response: `ApiFilesSummary`
Field
Type
Description
file\_summary\_info
ApiFileSummaryInfo
Field
Type
total\_file\_count
int64
file\_types
repeated ApiFileExtensionSummaryInfo
Field
Type
extension
string
file\_count
int64
total\_size
int64
column\_summary\_info
ApiColumnSummaryInfo
Field
Type
total\_column\_count
int64
column\_types
repeated ApiColumnTypeSummaryInfo
Field
Type
column\_type
string
column\_count
int64
##### Request: `ApiGetDatasetMetadataRequest`
Field
Type
Description
owner\_slug
string
The slug of the owner of the dataset.
dataset\_slug
string
The slug of the dataset.
##### Response: `ApiGetDatasetMetadataResponse`
Field
Type
Description
info
DatasetInfo
Field
Type
dataset\_id
int32
dataset\_slug
string
owner\_user
string
usability\_rating
double
total\_views
int32
total\_votes
int32
total\_downloads
int32
title
string
subtitle
string
description
string
is\_private
bool
keywords
repeated string
licenses
repeated SettingsLicense
Field
Type
name
string
collaborators
repeated DatasetCollaborator
Field
Type
username
string
group\_slug
string
role
kaggle.users.CollaboratorType
data
repeated DatasetSettingsFile
Field
Type
name
string
description
string
total\_bytes
int64
columns
repeated DatasetSettingsFileColumn
Field
Type
name
string
description
string
type
string
error\_message
string
##### Request: `ApiGetDatasetStatusRequest`
Field
Type
Description
owner\_slug
string
The slug of the owner of the dataset.
dataset\_slug
string
The slug of the dataset.
##### Response: `ApiGetDatasetStatusResponse`
Field
Type
Description
status
DatabundleVersionStatus
The processing status of a dataset. Possible values: DRAFT, PROCESSING, READY, ERROR, DELETED, PROCESSING\_ERROR.
##### Request: `ApiListDatasetFilesRequest`
Field
Type
Description
owner\_slug
string
The slug of the owner of the dataset.
dataset\_slug
string
The slug of the dataset.
dataset\_version\_number
int32
The version number of the dataset.
page\_token
string
The page token to use for pagination.
page\_size
int32
The number of items to return.
##### Response: `ApiListDatasetFilesResponse`
Field
Type
Description
dataset\_files
repeated ApiDatasetFile
Field
Type
ref
string
dataset\_ref
string
owner\_ref
string
name
string
creation\_date
google.protobuf.Timestamp
description
string
file\_type
string
url
string
total\_bytes
int64
columns
repeated ApiDatasetColumn
Field
Type
order
int32
name
string
type
string
original\_type
string
description
string
error\_message
string
next\_page\_token
string
##### Request: `ApiListDatasetsRequest`
Field
Type
Description
group
DatasetSelectionGroup
Possible values: DATASET\_SELECTION\_GROUP\_PUBLIC, DATASET\_SELECTION\_GROUP\_MY, DATASET\_SELECTION\_GROUP\_USER, DATASET\_SELECTION\_GROUP\_USER\_SHARED\_WITH\_ME, DATASET\_SELECTION\_GROUP\_UPVOTED, DATASET\_SELECTION\_GROUP\_MY\_PRIVATE, DATASET\_SELECTION\_GROUP\_MY\_PUBLIC, DATASET\_SELECTION\_GROUP\_ORGANIZATION, DATASET\_SELECTION\_GROUP\_BOOKMARKED, DATASET\_SELECTION\_GROUP\_COLLABORATION, DATASET\_SELECTION\_GROUP\_SHARED\_WITH\_USER, DATASET\_SELECTION\_GROUP\_FEATURED, DATASET\_SELECTION\_GROUP\_ALL, DATASET\_SELECTION\_GROUP\_UNFEATURED.
sort\_by
DatasetSortBy
Possible values: DATASET\_SORT\_BY\_HOTTEST, DATASET\_SORT\_BY\_VOTES, DATASET\_SORT\_BY\_UPDATED, DATASET\_SORT\_BY\_ACTIVE, DATASET\_SORT\_BY\_PUBLISHED, DATASET\_SORT\_BY\_RELEVANCE, DATASET\_SORT\_BY\_LAST\_VIEWED, DATASET\_SORT\_BY\_USABILITY, DATASET\_SORT\_BY\_DOWNLOAD\_COUNT, DATASET\_SORT\_BY\_NOTEBOOK\_COUNT.
size
DatasetSizeGroup
Possible values: DATASET\_SIZE\_GROUP\_ALL, DATASET\_SIZE\_GROUP\_SMALL, DATASET\_SIZE\_GROUP\_MEDIUM, DATASET\_SIZE\_GROUP\_LARGE.
file\_type
DatasetFileTypeGroup
Possible values: DATASET\_FILE\_TYPE\_GROUP\_ALL, DATASET\_FILE\_TYPE\_GROUP\_CSV, DATASET\_FILE\_TYPE\_GROUP\_SQLITE, DATASET\_FILE\_TYPE\_GROUP\_JSON, DATASET\_FILE\_TYPE\_GROUP\_BIG\_QUERY, DATASET\_FILE\_TYPE\_GROUP\_PARQUET.
license
DatasetLicenseGroup
Possible values: DATASET\_LICENSE\_GROUP\_ALL, DATASET\_LICENSE\_GROUP\_CC, DATASET\_LICENSE\_GROUP\_GPL, DATASET\_LICENSE\_GROUP\_ODB, DATASET\_LICENSE\_GROUP\_OTHER.
viewed
DatasetViewedGroup
Possible values: DATASET\_VIEWED\_GROUP\_UNSPECIFIED, DATASET\_VIEWED\_GROUP\_VIEWED.
tag\_ids
string
The tag IDs to filter by.
search
string
The search terms to filter by.
user
string
The user to filter by.
min\_size
int64
The minimum size of the dataset in bytes.
max\_size
int64
The maximum size of the dataset in bytes.
page
int32
The page number.
page\_token
string
The page token to use for pagination.
page\_size
int32
The number of items to return.
##### Response: `ApiListDatasetsResponse`
Field
Type
Description
datasets
repeated ApiDataset
Field
Type
id
int32
ref
string
subtitle
string
creator\_name
string
creator\_url
string
total\_bytes
int64
url
string
last\_updated
google.protobuf.Timestamp
download\_count
int32
is\_private
bool
is\_featured
bool
license\_name
string
description
string
owner\_name
string
owner\_ref
string
kernel\_count
int32
title
string
topic\_count
int32
view\_count
int32
vote\_count
int32
current\_version\_number
int32
usability\_rating
float
tags
repeated ApiCategory
Field
Type
ref
string
name
string
description
string
full\_path
string
competition\_count
int32
dataset\_count
int32
script\_count
int32
total\_count
int32
files
repeated ApiDatasetFile
Field
Type
ref
string
dataset\_ref
string
owner\_ref
string
name
string
creation\_date
google.protobuf.Timestamp
description
string
file\_type
string
url
string
total\_bytes
int64
columns
repeated ApiDatasetColumn
Field
Type
order
int32
name
string
type
string
original\_type
string
description
string
versions
repeated ApiDatasetVersion
Field
Type
version\_number
int32
creation\_date
google.protobuf.Timestamp
creator\_name
string
creator\_ref
string
version\_notes
string
status
string
thumbnail\_image\_url
string
next\_page\_token
string
##### Request: `ApiListTreeDatasetFilesRequest`
Field
Type
Description
owner\_slug
string
The slug of the owner of the dataset.
dataset\_slug
string
The slug of the dataset.
dataset\_version\_number
int32
The version number of the dataset.
path
string
The path of the directory to list files from.
page\_token
string
The page token to use for pagination.
page\_size
int32
The number of items to return.
##### Response: `ApiDirectoryContent`
##### Request: `ApiUpdateDatasetMetadataRequest`
Field
Type
Description
owner\_slug
string
The slug of the owner of the dataset.
dataset\_slug
string
The slug of the dataset.
settings
DatasetSettings
Field
Type
title
string
subtitle
string
description
string
is\_private
bool
keywords
repeated string
licenses
repeated SettingsLicense
Field
Type
name
string
collaborators
repeated DatasetCollaborator
Field
Type
username
string
group\_slug
string
role
kaggle.users.CollaboratorType
data
repeated DatasetSettingsFile
Field
Type
name
string
description
string
total\_bytes
int64
columns
repeated DatasetSettingsFileColumn
Field
Type
name
string
description
string
type
string
The new settings for the dataset.
##### Response: `ApiUpdateDatasetMetadataResponse`
##### Request: `ApiUploadDatasetFileRequest`
Field
Type
Description
file\_name
string
The name of the file to upload.
content\_length
int64
The length of the file in bytes.
last\_modified\_epoch\_seconds
int64
The last modified time of the file in epoch seconds.
##### Response: `ApiUploadDatasetFileResponse`
### Models
##### Request: `ApiCreateModelRequest`
Field
Type
Description
owner\_slug
string
The slug of the owner of the model.
slug
string
The slug of the model.
title
string
The title of the model.
subtitle
string
The subtitle of the model.
is\_private
bool
Whether the model is private.
description
string
The description of the model.
publish\_time
google.protobuf.Timestamp
The time to publish the model.
provenance\_sources
string
The provenance sources of the model.
##### Response: `ApiCreateModelResponse`
##### Request: `ApiCreateModelInstanceRequest`
Field
Type
Description
owner\_slug
string
The slug of the owner of the model.
model\_slug
string
The slug of the model.
body
ApiCreateModelInstanceRequestBody
Field
Type
instance\_slug
string
framework
ModelFramework
overview
string
usage
string
fine\_tunable
bool
training\_data
repeated string
files
repeated kaggle.datasets.ApiDatasetNewFile
Field
Type
file\_name
string
content
bytes
content\_type
string
directories
repeated kaggle.datasets.ApiUploadDirectoryInfo
license\_name
string
model\_instance\_type
ModelInstanceType
base\_model\_instance
string
external\_base\_model\_url
string
sigstore
bool
The request body.
##### Response: `ApiCreateModelResponse`
##### Request: `ApiCreateModelInstanceVersionRequest`
Field
Type
Description
owner\_slug
string
The slug of the owner of the model.
model\_slug
string
The slug of the model.
framework
ModelFramework
Possible values: MODEL\_FRAMEWORK\_UNSPECIFIED, MODEL\_FRAMEWORK\_TENSOR\_FLOW\_1, MODEL\_FRAMEWORK\_TENSOR\_FLOW\_2, MODEL\_FRAMEWORK\_TF\_LITE, MODEL\_FRAMEWORK\_TF\_JS, MODEL\_FRAMEWORK\_PY\_TORCH, MODEL\_FRAMEWORK\_JAX, MODEL\_FRAMEWORK\_FLAX, MODEL\_FRAMEWORK\_PAX, MODEL\_FRAMEWORK\_MAX\_TEXT, MODEL\_FRAMEWORK\_GEMMA\_CPP, MODEL\_FRAMEWORK\_GGML, MODEL\_FRAMEWORK\_GGUF, MODEL\_FRAMEWORK\_CORAL, MODEL\_FRAMEWORK\_SCIKIT\_LEARN, MODEL\_FRAMEWORK\_MXNET, MODEL\_FRAMEWORK\_ONNX, MODEL\_FRAMEWORK\_KERAS, MODEL\_FRAMEWORK\_TRANSFORMERS, MODEL\_FRAMEWORK\_API, MODEL\_FRAMEWORK\_OTHER, MODEL\_FRAMEWORK\_TENSOR\_RT\_LLM, MODEL\_FRAMEWORK\_TRITON.
instance\_slug
string
The slug of the model instance.
body
ApiCreateModelInstanceVersionRequestBody
Field
Type
version\_notes
string
files
repeated kaggle.datasets.ApiDatasetNewFile
Field
Type
file\_name
string
content
bytes
content\_type
string
directories
repeated kaggle.datasets.ApiUploadDirectoryInfo
sigstore
bool
The request body.
##### Response: `ApiCreateModelResponse`
##### Request: `ApiDownloadModelInstanceVersionRequest`
Field
Type
Description
owner\_slug
string
The slug of the owner of the model.
model\_slug
string
The slug of the model.
framework
ModelFramework
Possible values: MODEL\_FRAMEWORK\_UNSPECIFIED, MODEL\_FRAMEWORK\_TENSOR\_FLOW\_1, MODEL\_FRAMEWORK\_TENSOR\_FLOW\_2, MODEL\_FRAMEWORK\_TF\_LITE, MODEL\_FRAMEWORK\_TF\_JS, MODEL\_FRAMEWORK\_PY\_TORCH, MODEL\_FRAMEWORK\_JAX, MODEL\_FRAMEWORK\_FLAX, MODEL\_FRAMEWORK\_PAX, MODEL\_FRAMEWORK\_MAX\_TEXT, MODEL\_FRAMEWORK\_GEMMA\_CPP, MODEL\_FRAMEWORK\_GGML, MODEL\_FRAMEWORK\_GGUF, MODEL\_FRAMEWORK\_CORAL, MODEL\_FRAMEWORK\_SCIKIT\_LEARN, MODEL\_FRAMEWORK\_MXNET, MODEL\_FRAMEWORK\_ONNX, MODEL\_FRAMEWORK\_KERAS, MODEL\_FRAMEWORK\_TRANSFORMERS, MODEL\_FRAMEWORK\_API, MODEL\_FRAMEWORK\_OTHER, MODEL\_FRAMEWORK\_TENSOR\_RT\_LLM, MODEL\_FRAMEWORK\_TRITON.
instance\_slug
string
The slug of the model instance.
version\_number
int32
The version number of the model instance.
path
string
Relative path to a specific file inside the databundle.
##### Response: `HttpRedirect`
Returns a URL to download the model instance version.
##### Request: `ApiGetModelRequest`
Field
Type
Description
owner\_slug
string
The slug of the owner of the model.
model\_slug
string
The slug of the model.
##### Response: `ApiModel`
Field
Type
Description
id
int32
ref
string
title
string
subtitle
string
author
string
slug
string
is\_private
bool
description
string
instances
repeated ApiModelInstance
Field
Type
id
int32
slug
string
framework
ModelFramework
fine\_tunable
bool
overview
string
usage
string
download\_url
string
version\_id
int32
version\_number
int32
training\_data
repeated string
url
string
license\_name
string
model\_instance\_type
ModelInstanceType
base\_model\_instance\_information
BaseModelInstanceInformation
Field
Type
id
int32
owner
Owner
Field
Type
id
int32
image\_url
string
is\_organization
bool
name
string
profile\_url
string
slug
string
user\_tier
kaggle.users.UserAchievementTier
user\_progression\_opt\_out
bool
allow\_model\_gating
bool
model\_slug
string
instance\_slug
string
framework
ModelFramework
external\_base\_model\_url
string
total\_uncompressed\_bytes
int64
tags
repeated kaggle.datasets.ApiCategory
Field
Type
ref
string
name
string
description
string
full\_path
string
competition\_count
int32
dataset\_count
int32
script\_count
int32
total\_count
int32
publish\_time
google.protobuf.Timestamp
provenance\_sources
string
url
string
model\_version\_links
repeated ModelLink
Field
Type
type
ModelVersionLinkType
url
string
vote\_count
int32
author\_image\_url
string
update\_time
google.protobuf.Timestamp
##### Request: `ApiGetModelInstanceRequest`
Field
Type
Description
owner\_slug
string
The slug of the owner of the model.
model\_slug
string
The slug of the model.
framework
ModelFramework
Possible values: MODEL\_FRAMEWORK\_UNSPECIFIED, MODEL\_FRAMEWORK\_TENSOR\_FLOW\_1, MODEL\_FRAMEWORK\_TENSOR\_FLOW\_2, MODEL\_FRAMEWORK\_TF\_LITE, MODEL\_FRAMEWORK\_TF\_JS, MODEL\_FRAMEWORK\_PY\_TORCH, MODEL\_FRAMEWORK\_JAX, MODEL\_FRAMEWORK\_FLAX, MODEL\_FRAMEWORK\_PAX, MODEL\_FRAMEWORK\_MAX\_TEXT, MODEL\_FRAMEWORK\_GEMMA\_CPP, MODEL\_FRAMEWORK\_GGML, MODEL\_FRAMEWORK\_GGUF, MODEL\_FRAMEWORK\_CORAL, MODEL\_FRAMEWORK\_SCIKIT\_LEARN, MODEL\_FRAMEWORK\_MXNET, MODEL\_FRAMEWORK\_ONNX, MODEL\_FRAMEWORK\_KERAS, MODEL\_FRAMEWORK\_TRANSFORMERS, MODEL\_FRAMEWORK\_API, MODEL\_FRAMEWORK\_OTHER, MODEL\_FRAMEWORK\_TENSOR\_RT\_LLM, MODEL\_FRAMEWORK\_TRITON.
instance\_slug
string
The slug of the model instance.
##### Response: `ApiModelInstance`
Field
Type
Description
id
int32
slug
string
framework
ModelFramework
fine\_tunable
bool
overview
string
usage
string
download\_url
string
version\_id
int32
version\_number
int32
training\_data
repeated string
url
string
license\_name
string
model\_instance\_type
ModelInstanceType
base\_model\_instance\_information
BaseModelInstanceInformation
Field
Type
id
int32
owner
Owner
Field
Type
id
int32
image\_url
string
is\_organization
bool
name
string
profile\_url
string
slug
string
user\_tier
kaggle.users.UserAchievementTier
user\_progression\_opt\_out
bool
allow\_model\_gating
bool
model\_slug
string
instance\_slug
string
framework
ModelFramework
external\_base\_model\_url
string
total\_uncompressed\_bytes
int64
##### Request: `ApiListModelsRequest`
Field
Type
Description
search
string
Display models matching the specified search terms.
sort\_by
ListModelsOrderBy
Sort the results. Possible values: LIST\_MODELS\_ORDER\_BY\_UNSPECIFIED, LIST\_MODELS\_ORDER\_BY\_HOTNESS, LIST\_MODELS\_ORDER\_BY\_DOWNLOAD\_COUNT, LIST\_MODELS\_ORDER\_BY\_VOTE\_COUNT, LIST\_MODELS\_ORDER\_BY\_NOTEBOOK\_COUNT, LIST\_MODELS\_ORDER\_BY\_PUBLISH\_TIME, LIST\_MODELS\_ORDER\_BY\_CREATE\_TIME, LIST\_MODELS\_ORDER\_BY\_UPDATE\_TIME, LIST\_MODELS\_ORDER\_BY\_VIEW\_TIME\_DESC.
owner
string
Display models by a particular user or organization.
page\_size
int32
Page size.
page\_token
string
Page token used for pagination.
only\_vertex\_models
bool
Only list models that have Vertex URLs.
##### Response: `ApiListModelsResponse`
Field
Type
Description
models
repeated ApiModel
Field
Type
id
int32
ref
string
title
string
subtitle
string
author
string
slug
string
is\_private
bool
description
string
instances
repeated ApiModelInstance
Field
Type
id
int32
slug
string
framework
ModelFramework
fine\_tunable
bool
overview
string
usage
string
download\_url
string
version\_id
int32
version\_number
int32
training\_data
repeated string
url
string
license\_name
string
model\_instance\_type
ModelInstanceType
base\_model\_instance\_information
BaseModelInstanceInformation
Field
Type
id
int32
owner
Owner
Field
Type
id
int32
image\_url
string
is\_organization
bool
name
string
profile\_url
string
slug
string
user\_tier
kaggle.users.UserAchievementTier
user\_progression\_opt\_out
bool
allow\_model\_gating
bool
model\_slug
string
instance\_slug
string
framework
ModelFramework
external\_base\_model\_url
string
total\_uncompressed\_bytes
int64
tags
repeated kaggle.datasets.ApiCategory
Field
Type
ref
string
name
string
description
string
full\_path
string
competition\_count
int32
dataset\_count
int32
script\_count
int32
total\_count
int32
publish\_time
google.protobuf.Timestamp
provenance\_sources
string
url
string
model\_version\_links
repeated ModelLink
Field
Type
type
ModelVersionLinkType
url
string
vote\_count
int32
author\_image\_url
string
update\_time
google.protobuf.Timestamp
next\_page\_token
string
total\_results
int64
##### Request: `ApiListModelInstancesRequest`
Field
Type
Description
owner\_slug
string
The slug of the owner of the model.
model\_slug
string
The slug of the model.
page\_size
int32
The number of items to return.
page\_token
string
The page token to use for pagination.
##### Response: `ApiListModelInstancesResponse`
Field
Type
Description
instances
repeated ModelInstance
Field
Type
id
int32
owner\_slug
string
model\_slug
string
model\_id
int32
slug
string
version\_id
int32
fine\_tunable
bool
overview
string
usage
string
rendered\_usage
string
text\_representation
string
source\_url
string
version\_number
int32
framework
ModelFramework
version\_notes
string
download\_url
string
databundle\_id
int32
databundle\_version\_id
int32
databundle\_version\_type
kaggle.datasets.DatabundleVersionType
firestore\_path
string
status
kaggle.datasets.DatabundleVersionStatus
creation\_status
kaggle.datasets.DatabundleVersionCreationStatus
error\_message
string
last\_version\_id
int32
source\_organization
Owner
Field
Type
id
int32
image\_url
string
is\_organization
bool
name
string
profile\_url
string
slug
string
user\_tier
kaggle.users.UserAchievementTier
user\_progression\_opt\_out
bool
allow\_model\_gating
bool
training\_data
repeated string
metrics
string
license\_post
LicensePost
Field
Type
id
int32
content
string
license
kaggle.licenses.License
Field
Type
id
int32
name
string
url
string
agreement\_required
bool
agreement\_status
UserLicenseAgreementStatus
consent\_time
google.protobuf.Timestamp
current\_revision\_number
int32
can\_use
bool
uncompressed\_storage\_uri
string
model\_instance\_type
ModelInstanceType
base\_model\_instance\_id
int32
base\_model\_instance\_information
BaseModelInstanceInformation
Field
Type
id
int32
owner
Owner
Field
Type
id
int32
image\_url
string
is\_organization
bool
name
string
profile\_url
string
slug
string
user\_tier
kaggle.users.UserAchievementTier
user\_progression\_opt\_out
bool
allow\_model\_gating
bool
model\_slug
string
instance\_slug
string
framework
ModelFramework
external\_base\_model\_url
string
download\_summary
ModelInstanceDownloadSummary
Field
Type
total\_downloads
double
download\_series\_points
repeated ModelActivityTimeSeriesPoint
Field
Type
date
google.protobuf.Timestamp
count
int32
model\_instance\_id
int32
total\_uncompressed\_bytes
int64
sigstore\_state
SigstoreState
created\_by\_kernel\_id
int32
creator\_user\_id
int32
attestation\_kernel\_url
string
next\_page\_token
string
##### Request: `ApiListModelInstanceVersionsRequest`
Field
Type
Description
owner\_slug
string
The slug of the owner of the model.
model\_slug
string
The slug of the model.
instance\_slug
string
The slug of the model instance.
framework
ModelFramework
Possible values: MODEL\_FRAMEWORK\_UNSPECIFIED, MODEL\_FRAMEWORK\_TENSOR\_FLOW\_1, MODEL\_FRAMEWORK\_TENSOR\_FLOW\_2, MODEL\_FRAMEWORK\_TF\_LITE, MODEL\_FRAMEWORK\_TF\_JS, MODEL\_FRAMEWORK\_PY\_TORCH, MODEL\_FRAMEWORK\_JAX, MODEL\_FRAMEWORK\_FLAX, MODEL\_FRAMEWORK\_PAX, MODEL\_FRAMEWORK\_MAX\_TEXT, MODEL\_FRAMEWORK\_GEMMA\_CPP, MODEL\_FRAMEWORK\_GGML, MODEL\_FRAMEWORK\_GGUF, MODEL\_FRAMEWORK\_CORAL, MODEL\_FRAMEWORK\_SCIKIT\_LEARN, MODEL\_FRAMEWORK\_MXNET, MODEL\_FRAMEWORK\_ONNX, MODEL\_FRAMEWORK\_KERAS, MODEL\_FRAMEWORK\_TRANSFORMERS, MODEL\_FRAMEWORK\_API, MODEL\_FRAMEWORK\_OTHER, MODEL\_FRAMEWORK\_TENSOR\_RT\_LLM, MODEL\_FRAMEWORK\_TRITON.
page\_size
int32
The number of items to return.
page\_token
string
The page token to use for pagination.
##### Response: `ApiListModelInstanceVersionsResponse`
Field
Type
Description
version\_list
ModelInstanceVersionList
Field
Type
versions
repeated ModelInstanceVersion
Field
Type
id
int32
framework
ModelFramework
is\_tfhub\_model
bool
url
string
variation\_slug
string
version\_number
int32
model\_title
string
thumbnail\_url
string
is\_private
bool
sigstore\_state
SigstoreState
next\_page\_token
string
##### Request: `ApiListModelInstanceVersionFilesRequest`
Field
Type
Description
owner\_slug
string
The slug of the owner of the model.
model\_slug
string
The slug of the model.
instance\_slug
string
The slug of the model instance.
framework
ModelFramework
Possible values: MODEL\_FRAMEWORK\_UNSPECIFIED, MODEL\_FRAMEWORK\_TENSOR\_FLOW\_1, MODEL\_FRAMEWORK\_TENSOR\_FLOW\_2, MODEL\_FRAMEWORK\_TF\_LITE, MODEL\_FRAMEWORK\_TF\_JS, MODEL\_FRAMEWORK\_PY\_TORCH, MODEL\_FRAMEWORK\_JAX, MODEL\_FRAMEWORK\_FLAX, MODEL\_FRAMEWORK\_PAX, MODEL\_FRAMEWORK\_MAX\_TEXT, MODEL\_FRAMEWORK\_GEMMA\_CPP, MODEL\_FRAMEWORK\_GGML, MODEL\_FRAMEWORK\_GGUF, MODEL\_FRAMEWORK\_CORAL, MODEL\_FRAMEWORK\_SCIKIT\_LEARN, MODEL\_FRAMEWORK\_MXNET, MODEL\_FRAMEWORK\_ONNX, MODEL\_FRAMEWORK\_KERAS, MODEL\_FRAMEWORK\_TRANSFORMERS, MODEL\_FRAMEWORK\_API, MODEL\_FRAMEWORK\_OTHER, MODEL\_FRAMEWORK\_TENSOR\_RT\_LLM, MODEL\_FRAMEWORK\_TRITON.
version\_number
int32
The version number of the model instance.
page\_size
int32
The number of items to return.
page\_token
string
The page token to use for pagination.
##### Response: `ApiListModelInstanceVersionFilesResponse`
Field
Type
Description
files
repeated ApiModelFile
Field
Type
name
string
size
int64
creation\_date
google.protobuf.Timestamp
next\_page\_token
string
##### Request: `ApiUpdateModelRequest`
Field
Type
Description
owner\_slug
string
The slug of the owner of the model.
model\_slug
string
The slug of the model.
title
string
The title of the model.
subtitle
string
The subtitle of the model.
is\_private
bool
Whether the model is private.
description
string
The description of the model.
publish\_time
google.protobuf.Timestamp
The time to publish the model.
provenance\_sources
string
The provenance sources of the model.
update\_mask
google.protobuf.FieldMask
The fields to update.
##### Response: `ApiUpdateModelResponse`
##### Request: `ApiUpdateModelInstanceRequest`
Field
Type
Description
owner\_slug
string
The slug of the owner of the model.
model\_slug
string
The slug of the model.
framework
ModelFramework
Possible values: MODEL\_FRAMEWORK\_UNSPECIFIED, MODEL\_FRAMEWORK\_TENSOR\_FLOW\_1, MODEL\_FRAMEWORK\_TENSOR\_FLOW\_2, MODEL\_FRAMEWORK\_TF\_LITE, MODEL\_FRAMEWORK\_TF\_JS, MODEL\_FRAMEWORK\_PY\_TORCH, MODEL\_FRAMEWORK\_JAX, MODEL\_FRAMEWORK\_FLAX, MODEL\_FRAMEWORK\_PAX, MODEL\_FRAMEWORK\_MAX\_TEXT, MODEL\_FRAMEWORK\_GEMMA\_CPP, MODEL\_FRAMEWORK\_GGML, MODEL\_FRAMEWORK\_GGUF, MODEL\_FRAMEWORK\_CORAL, MODEL\_FRAMEWORK\_SCIKIT\_LEARN, MODEL\_FRAMEWORK\_MXNET, MODEL\_FRAMEWORK\_ONNX, MODEL\_FRAMEWORK\_KERAS, MODEL\_FRAMEWORK\_TRANSFORMERS, MODEL\_FRAMEWORK\_API, MODEL\_FRAMEWORK\_OTHER, MODEL\_FRAMEWORK\_TENSOR\_RT\_LLM, MODEL\_FRAMEWORK\_TRITON.
instance\_slug
string
The slug of the model instance.
overview
string
The overview of the model instance.
usage
string
The usage of the model instance.
fine\_tunable
bool
Whether the model instance is fine-tunable.
training\_data
repeated string
The training data of the model instance.
update\_mask
google.protobuf.FieldMask
The fields to update.
license\_name
string
The name of the license.
model\_instance\_type
ModelInstanceType
Possible values: MODEL\_INSTANCE\_TYPE\_UNSPECIFIED, MODEL\_INSTANCE\_TYPE\_BASE\_MODEL, MODEL\_INSTANCE\_TYPE\_KAGGLE\_VARIANT, MODEL\_INSTANCE\_TYPE\_EXTERNAL\_VARIANT.
base\_model\_instance
string
The base model instance.
external\_base\_model\_url
string
The external base model URL.
##### Response: `ApiUpdateModelResponse`

# [Benchmarks Documentation](https://www.kaggle.com/docs/benchmarks) 
 _https://www.kaggle.com/docs/benchmarks_

* * *
### Overview
Kaggle seeks to be the home of a diverse ecosystem of high quality benchmarks assessing model capabilities on tasks of significant importance to the industry to help developers reliably understand and trust what works well on ML tasks. Building on Kaggle's decade-plus of experience as the home for hosting ML Competitions, which are a type of benchmark, for the industry and our partners, we will adhere to the following principles:
* Kaggle believes in the importance of **robustness**: enduring, high-value benchmarks that truly help the industry measure progress in AI are ones that can’t be easily hacked, saturated, or leaked
* Kaggle believes in the importance of **reproducibility and transparency** for ensuring the industry can trust benchmarks and evaluations. We also take in extremely high regard the trust publishers place in us as a platform.
* **Kaggle doesn’t develop benchmarks**. Our role is to independently reproduce and publicly release results, provide a model-agnostic platform that streamlines evaluation of new models on new benchmarks over time, and drive community engagement and stress testing.
[Kaggle Benchmarks](https://www.kaggle.com/benchmarks) comprises two main types of benchmarks: 1) **Research Benchmarks**, which are evals created by researchers working in AI labs, and 2) **Community Benchmarks**, which are evals created by the Kaggle community.
Both are technically identical, with the only difference being that Research Benchmarks tend to require a lot more compute. If you're a researcher who wants to host your benchmarks with us, email kaggle-benchmarks@google.com to discuss how you can get a higher quota.
* * *
### Creating Tasks and Benchmarks
First, some key concepts about Kaggle Benchmarks:
* **Task:** A Python function defining the problem (e.g., "Solve this riddle").
* **Benchmark:** A collection of tasks that you can put together. There is no code implementation for this. This is a feature that Kaggle supports on the graphical user interface so that users can put together their own benchmarks based on the tasks that they care about
#### Creating a Task
📺 **Video Guide**: [How to create a task](https://www.youtube.com/watch?v=brIF5xGPkcM)
* 1\. Go to [Kaggle Benchmarks](https://www.kaggle.com/benchmarks) and click "Create task"
* 2\. Create a new task - you can either write the code from scratch or prompt an AI to generate the code for you
* ⚠️ Access Requirements: Please ensure your account is phone-verified to access resources such as LLM API quotas. Furthermore, accounts registered after December 15, 2025, must complete additional identity verification to execute task notebooks.
 * 3\. Once the task notebook has been created, you can make edits to it. Once it's done, you can run it in the notebook or "Save Task", which will create a Task Detail page
* 4\. The Task Detail page is where you can add a description, new models to be evaluated, compare outputs across different models, and even share it with others
To get started creating your first task, check out the [Getting Started Notebook](https://www.kaggle.com/code/nicholaskanggoog/kaggle-benchmarks-getting-started-notebook?scriptVersionId=290215074).
#### Creating a Benchmark
Remember that a benchmark is simply multiple tasks put together into a collection.
📺 **Video Guide**: [How to create a benchmark](https://www.youtube.com/watch?v=V5tkw8zZJJc)
* 1\. Go to [Kaggle Benchmarks](https://www.kaggle.com/benchmarks) and click "Create benchmark"
* 2\. Fill in the information in the panel. You can always change names and descriptions later!
* 3\. You should be brought to the Benchmark Detail page, where you will need to add tasks to your benchmark. You can add your own tasks or public tasks that others have created.
* 4\. Next, you will need to add a list of models that you want to display on the benchmark page.
* 5\. Once that's done, you will see your completed Benchmark detail page. You can edit, share, and add new models and tasks!
* * *
### Downloading Benchmark Leaderboards
You can download the benchmark leaderboard data for your own analysis. There are two ways to access the download options:
* From the three-dot menu ("︙") in the top right of the benchmark page.
* Using the "Download" button located directly above the leaderboard table.
Both actions open a download popup that provides methods to retrieve the data.
#### Download via API
The popup provides a cURL command to download the leaderboard data as a JSON object. If the Benchmark is not public, you will need to authenticate using your Kaggle credentials.
＃ Unauthenticated example
curl -L -o ~/Downloads/open-benchmarks_scicode_leaderboard.json \
 https://www.kaggle.com/api/v1/benchmarks/open-benchmarks/scicode/leaderboard
# Authenticated example
# Export your Kaggle username and API key
# export KAGGLE_USERNAME=
# export KAGGLE_KEY=
curl -L -u $KAGGLE_USERNAME:$KAGGLE_KEY \
 -o ~/Downloads/myusername_my-benchmark_leaderboard.json \
 https://www.kaggle.com/api/v1/benchmarks/myusername/my-benchmark/leaderboard
#### Download as CSV
At the bottom of the download popup, you can click "Download leaderboard as csv" to directly download the data as a CSV file.
* * *
### Models
#### Supported Models in Community Benchmarks
We continue to update the list of available models in Community Benchmarks as new models are released and old models are deprecated. We currently do not support some models (e.g. OpenAI models), but are working on growing our list over time. To query the current list of supported models, run the following command in the task notebook:
import kaggle\_benchmarks as kbench
# returns the current list of available models to test against
list(kbench.llms.keys())
#### Supported Models in Research Benchmarks
Model selection within Research Benchmarks is determined by the specific evaluation and the researchers involved. Consequently, these may include supplemental models not currently supported in Community Benchmarks.
* * *
### Learning resources
* [Getting started notebook](https://www.kaggle.com/code/nicholaskanggoog/kaggle-benchmarks-getting-started-notebook?scriptVersionId=290215074)
* [Kaggle Benchmarks GitHub repo](https://github.com/Kaggle/kaggle-benchmarks)
* [Kaggle Community Benchmarks NotebookLM](https://notebooklm.google.com/notebook/56661d72-a74b-48cc-a2d0-08a6f7a595e8)

# [Models Documentation](https://www.kaggle.com/docs/models) 
 _https://www.kaggle.com/docs/models_

* * *
### What is Kaggle Models
[Kaggle Models](https://www.kaggle.com/models) provides a way to discover, use, and share models for machine learning and generative AI applications. Kaggle Models is a repository of pre-trained models that are deeply integrated with Kaggle's platform, making them easy to use in Kaggle Competitions and Notebooks. Like Datasets, Kaggle Models organize community activity that enrich models' usefulness: every model page will contain discussions, public notebooks, and usage statistics like downloads and upvotes that make models more useful.
#### Where do Models come from?
Kaggle Models come from a variety of sources including partners that we collaborate with on releases like Meta's Llama 2 and Alibaba's Qwen, integrations with modeling libraries like Keras, [integrations with Hugging Face Hub](https://www.kaggle.com/blog/kaggle-hugging-face-integration), and the community of millions of Kagglers sharing fine-tuned variants and other innovations.
* * *
### Finding Kaggle Models
You can find Kaggle Models by using the [Models landing page](https://www.kaggle.com/models). There are a number of filters and sorts plus free text search. For instances you can search by:
* Filtering by Organization, Community, or Hugging Face models
* Filtering by framework
* Filtering by the task tag you want (e.g., classification)
* Filtering by model size
* Searching by keywords in the free text search
* Sorting by number of upvotes
* Etc.
You may also want to peruse the "Models" tab on competitions to see what models are performing well or are otherwise popular for tasks relevant to your use case. Competitors commonly share which models they're using in public notebooks and in discussion write-ups. When you fork a notebook that has a model from Kaggle Models attached to it, your copy will also have the same model attached.
Finally, you can also search for models from within the notebook editor. Use the "Add Models" component in the right-hand pane of the editor to search and attach models to your notebooks. This works similarly to Datasets.
#### Understanding the model detail page
When you click on a model you will be taken to the "detail page" for that model. For example, this is the detail page for a [BERT model](https://www.kaggle.com/models/google/bert). The model detail page contains an overview tab with a Model Card (metadata and information about how the model was trained, what its acceptable use cases are, any limitations, etc.), a framework and variation explorer, and a usage dashboard. There are tabs for notebooks and discussions. If a model is useful, you can upvote it.
Beyond the overall metadata, a model detail page also organizes all variations and frameworks for a given model. For example:
* **Variations**: The same model with different numbers of parameters, e.g., small, medium, and large.
* **Frameworks**: The same model with different ML library compatibility, e.g., TensorFlow, PyTorch, etc.
You can view and use the specific framework and variation that you want by selecting it in the file explorer on the overview page beneath the Model Card. From here, you can use click "New Notebook" to attach it to a new notebook to start using the model.
### Using Kaggle Models
There's two broad ways that Kaggle Models are useful: on Kaggle and outside of Kaggle (e.g., in production applications or using non-Kaggle tools like Colab, etc.).
**On Kaggle**
Currently, Kaggle Models are very useful within the context of Competitions, specifically for use within Notebooks. Start by either forking a notebook that has a model attached (you can view the attached models on the "Input" tab of any notebook), creating a new notebook on a model, or adding a model to a new notebook from the right-hand pane of the editor.
You'll be prompted to confirm your framework and model variations(s), then simply copy and paste the starter code to load the model.
If you are downloading a Hugging Face model in your notebook, e.g., by using the Transformers library, you don't have to do anything special to use Kaggle Models. A model page will be automatically "attached" to your notebook for you.
**Outside of Kaggle**
Many developers will need to download models in code outside of Kaggle. There are a few different methods: via the [kagglehub Python library](https://github.com/Kaggle/kagglehub), via our [Kaggle CLI](https://github.com/Kaggle/kaggle-cli), or by calling the API directly.
Before providing instructions for each of these methods, it's helpful to know that you will need to know how to authenticate in order to access certain models like [Gemma](https://www.kaggle.com/models/google/gemma) that require Kaggle credentials in order to confirm that user consent to the custom license has been verified. [Obtain credentials](https://www.kaggle.com/settings) from the “Settings” page when logged-in to Kaggle and clicking on the "Generate New Token" button under the "API" section.
The examples below allow you to download the `2b` PyTorch variation for the [google/gemma](https://www.kaggle.com/models/google/gemma) model. If a model doesn't have a restricted license like Gemma, you'll be able to skip the `kagglehub.login()` steps in the examples below.
#### Method 1. Via the kagglehub Python library
See [kagglehub model download documentation](https://github.com/Kaggle/kagglehub?tab=readme-ov-file#download-model).
#### Method 2. Via the Kaggle CLI
See [Kaggle CLI model download documentation](https://github.com/Kaggle/kagglehub?tab=readme-ov-file#download-model).
#### Method 3. Calling the API directly
＃ Authenticate with credentials
export KAGGLE_USERNAME=xyz
export KAGGLE_KEY=xyz
# With Curl
curl -L -o ~/Downloads/model.tar.gz https://www.kaggle.com/api/v1/models/google/gemma/pyTorch/2b/1/download -u $KAGGLE_USERNAME:$KAGGLE_KEY
# Download specific version (here version 1)
wget https://www.kaggle.com/api/v1/models/google/gemma/pyTorch/2b/1/download --user=$KAGGLE_USERNAME --password=$KAGGLE_KEY --auth-no-challenge
* * *
### Creating a Model
There are a few ways to publish a model on Kaggle Models including exclusively via the UI. We recommend using a combination of `kagglehub`, our Python client library, to manage artifact creation and uploads and the UI to manage documentation and collaborative features. And, if you want to use a Hugging Face model on Kaggle, you simply need to create a notebook that uses the model, e.g., in Transformers, and a model page on Kaggle will be created automatically for you.
#### Uploading using kagglehub Python client library (preferred)
See [kagglehub model upload documentation](https://github.com/Kaggle/kagglehub?tab=readme-ov-file#upload-model).
#### Uploading using the Kaggle CLI
See [Kaggle CLI model creation tutorial](https://github.com/Kaggle/kaggle-cli/blob/main/docs/tutorials.md#tutorial-create-a-model-variation).
#### Upload via the UI
1. Go to: [https://www.kaggle.com/models?new=true](https://www.kaggle.com/models?new=true) and follow the steps including setting “Creating As” to the Organization Profile you want to publish under
2. To add new Variations once your model is initially created:
1. Scroll down to the "Model Variations" section.
2. Click on the "New Variation" button to open the "Add/Edit" Variations modal.
3. Select the ML framework for which you want to update weights / assets for.
4. Click on the "Add new variation" button
5. Select the weight / assets files to upload
6. Enter the variation slug
1. For example, `7b`
2. Select a license
8. Click on the "Create" button and wait until your instance has been fully processed.
9. Click on "Go to model detail page".
10. In the "Model Variations" section, you should see your variation in the drop-down.
11. If you select it, confirm that you have all the files you were expecting under the "File Explorer" section.
12. To upload a new version for an existing variation. Use the "New Version" button.
#### Create via Hugging Face Integration
If you have published a model on Hugging Face Hub, you can create a page for it on Kaggle easily by simply using your model in a Kaggle Notebook.
1. Navigate to your model page on Hugging Face
2. Click "Use this model" in the page header
3. Select "Kaggle" from the drop down to create a Kaggle Notebook
4. If you're not already logged-in, you will be prompted to do so
5. Optionally make changes to your notebook
6. Give your notebook a name and create a "Save Version"
7. Optionally click "Share" to make your notebook public
Once you complete these steps, a page for your model will be automatically created. Any public notebooks using the model will show up in the "Code" tab on the model page.
#### Documenting models
Documenting your model is easiest to do via the UI.
1. When viewing your model page, you will see a section at the top called “Pending Actions”.
2. Follow each of these steps to complete your model’s documentation:
1. Add a description (model card)
2. Add model instance descriptions including example code
3. Add a subtitle
4. Add tags
5. Specify provenance and other metadata
6. Publish a notebook (we recommend making it public after your model is made public)
4. Once your model is made public, you can also optionally generate a DOI from the “Metadata” section of your model.
5. Once you’re done, you can make your model public from the “Settings” tab on the model page.
6. You can now promote your model!
7. You’ll be automatically subscribed to email and site notifications when any discussion topics are created
#### Importing Model Versions
This tool allows you to copy model versions from one model to another. You can import versions from any public model or private models where you have collaborator access.
1. Navigate to your target model's page on Kaggle
 1. Click the "︙" button in the top right
 2. Select "Import Versions" from the dropdown menu
2. Select Source Model:
 1. Click the "Select Model" button
 2. Browse or search for the model you want to import versions from
 1. You can only select models you own or have collaborator access to
 2. The current model will be disabled to prevent self-copying
 3. Click on your chosen model to select it
3. Select Versions:
 1. Once you've selected a source model, you'll see all available versions
 2. Use the search bar to filter versions by name
 3. Use the framework chips to filter by specific frameworks (PyTorch, TensorFlow, etc.)
 4. Select versions by checking the boxes in the leftmost column
 1. You can select multiple versions at once
 5. Click "Next" to proceed to confirmation
4. Confirm and Import:
 1. Review the versions you selected
 1. Each row shows the full path of what will be copied
 2. Source path → Target path is displayed
 2. Important notes:
 1. If importing from a private model to a public model, versions will become public permanently
 2. This action cannot be undone
 3. Click "Import" to begin the copy process
5. After Import:
 1. A progress indicator will show while versions are being copied
 2. For successful imports:
 1. You'll see a success message
 2. Click "Go to Model" to view your imported versions
 3. If any versions fail to import:
 1. Error messages will explain what went wrong
 2. You can retry failed imports by clicking "Try again"
 3. Successfully copied versions will not be duplicated on retry
##### Tips for Importing
* You can swap the source model at any time using the "Swap model" button
* Use framework filters to quickly find specific versions
* The version count shows how many items you've selected
* All imported versions maintain their original framework and variation slugs
### How to name your model and variations
A handle is represented as
###### owner\_slug/model\_slug/framework/variation\_slug/version\_number
The breakdown is as follows:
* **owner\_slug:** Your organization or username.
* **model\_slug:** The name of your model family (e.g., "llama").
* **framework:** The model framework used (e.g., "pytorch").
* **variation\_slug:** Details about this specific version of your model.
* **version\_number:** A numeric identifier for tracking model changes.
#### Model vs. Variation: Uniqueness
A variation is used to add finer level details about a model. A variation should capture the intricacies and nuances of a model. They highlight specific changes or features. Examples include:
* **Model Size:** Number of parameters (e.g., 7 billion)
* **Optimization:** Quantization (e.g., int4), model distillation
* **Task:** What your model does (e.g., image generation, translation, chat)
* **Training:** Specific techniques used (e.g., instruction-tuned, prompt-tuned)
* **Architecture/Code Modifications:** Any changes from the base model
* **Dataset:** The data it was trained on (if relevant)
* **Language:** If your model is language-specific (e.g., "en" for English)
* **Hardware:** Optimized for GPU, CPU, TPU, etc.
#### Version vs. Variation: Snapshots in Time
Versions are like checkpoints. They represent a model at a specific point in training, usually with all other factors (the variation details) held constant.
#### Questions to Guide Your Variation Naming:
1. How large is your model (number of parameters)? ex: 100m, 2b, 27b, etc..
2. What task does it perform? ex: image generation, text, chat
3. What dataset was it trained on? ex: coco, imagenet
4. Did you make any changes to the code, architecture, or configuration?
5. What training techniques did you use? ex: Instruction Tuned, Prompt Tuned, etc…
6. Is it optimized for a specific language or hardware? ex: gpu, cpu, tpu
7. Did you apply any quantization or other optimizations?
#### General Guidelines for Naming Success:
* **Keep it Simple:** Use clear, concise names.
* **Be Descriptive:** Use the questions above to guide you.
* **Default to Model Name:** If unsure, use the model name as the variation too.
* **Version for Checkpoints:** Use the version number to track training progress.
#### Real-World Examples
                                                                                          
Handle
Variation Note
google/gemma-2/gguf/2.0-27b-it/1
Version 2, 27 billion parameters, instruction tuned
google/gemma/tfLite/gemma-2b-it-gpu-int4/1
2 billion , instruction tuned, gpu, int4 quantization
metaresearch/llama-3/pyTorch/70b-chat
70 billion parameters, chating
mistral-ai/mistral/pyTorch/7b-v0.1-hf
7 billion parameters, version 0.1
deepmind/biggan/tensorFlow1/128
128 x 128 image generation
### Accessing Gated Models
A gated model on Kaggle requires users to agree to a specific agreement and potentially provide information before they can access it. This agreement can include terms of use, privacy policy links, and a form for collecting user data.
When accessing a gated model, users will be prompted to input information based on the access agreement. A banner will display the user's current access status (e.g., requiring a consent, pending, accepted, rejected). Only users with "accepted" status can proceed to use the model.

# [Kaggle Packages Documentation](https://www.kaggle.com/docs/packages) 
 _https://www.kaggle.com/docs/packages_

* * *
### Overview
Kaggle Packages are new functionality that lets you write Python Packages which can be imported and re-used elsewhere. We use the open-source `nbdev` library (more info on their [homepage](https://nbdev.fast.ai/)) to let you define a Python Package within a Kaggle Notebook, and our `kagglehub` library enables you to import and re-use it elsewhere.
One core benefit of Kaggle Packages is that it simplifies the user experience of participating in Code Competitions which support them. Previously, in most Code Competitions your Notebook would have to read the test set file(s) from Kaggle-specific filepaths, run the inference loop yourself while keeping track of a Kaggle-specific `id` column, then carefully package your predictions and `id` values into a `submission.csv` file written to another Kaggle-specific filepath. With Kaggle Packages, you no longer have to worry about those task-orthogonal details, instead you just write inference code which implements the competition's ML task and we take care of the rest.
Furthermore, Package submissions should be easier to re-use. You can use `kagglehub` to import a Package and call its code with arbitrary inputs anywhere. See below for more detailed instructions.
The initial intention is to use Kaggle Packages within (some) Code Competitions -- for example we're launching alongside the [Drawing With LLMs competition](https://www.kaggle.com/competitions/drawing-with-llms) -- though you can use them outside of Competitions as well, and we hope to expand our support there.
* * *
### What is a Kaggle Package
A Kaggle Package is a Python package generated from a Kaggle Notebook. It's created using `nbdev`, which exports specific cells (marked with ＃| export) from your notebook into Python files. The resulting Package is located in the `package` subdirectory of your Notebook's Output.
A Kaggle Package has the following structure:
* `__init__.py`: This file marks the directory as a Python package and defines metadata like the Docker Image and GPUs used when your Package was created, and optional Dependency Manager configuration.
* `*.py`: Submodule files contain the code you exported from your Notebook using `nbdev`. The ＃| default_exp directive in your Notebook determines the main module name (e.g., `core.py`).
* `assets/` (optional): This subdirectory stores any asset files your package needs, such as model weights, configuration files, or data files. You can access these files using `kagglehub.get_package_asset_path()`.
* `kagglehub_requirements.yaml`: This file lists the Kaggle resources (Datasets, Models, Notebooks, Packages) that your package depends on, including specific versions for reproducibility reasons.
Example Package Structure:
 package/
 ├── __init__.py
 ├── core.py
 ├── kagglehub_requirements.yaml
 └── assets/
 └── model.weights
* * *
### Creating a Package
To create a Kaggle Package, you'll write a Kaggle Notebook using `nbdev` conventions. Here's a breakdown of the process:
1. **Start with a Kaggle Notebook:** Create a new Kaggle Notebook or use an existing one.
2. **Use `nbdev` directives:**
 * Add ＃| default_exp core (or another module name) to a code cell. This is required and specifies the main module for your Package.
 * Mark the code cells you want to export with ＃| export. Only these cells will be included in your Package.
3. **Define your Package logic:** Write the code for your package, making sure to export the desired parts and not export undesired parts. This conditional export power is one main goal of the `nbdev` patterns, so you can define your exported Package and within the same Notebook also run other code which tests or analyzes your core functionality but which itself is \*not\* exported.
 * Make sure your exported code includes all `import` statements which its code requires.
 * Use `kagglehub` to refer to any Kaggle resources (Models, Datasets, Notebooks, other Packages). See below for more information.
 * For Code Competitions, we require a `class Model` with a `predict()` method meeting the competition's required input/output spec.
4. **Add Asset Files (Optional):** If your package needs external files, save them using `kagglehub.get_package_asset_path()` and have your Package code read the file using that same function.
5. **Configure Python Dependencies (Optional):** If you need Python Packages which are not available in our base environment, you can use our Dependency Manager to add them. See below for more information.
6. **Save Version:** When you Save your Notebook, Kaggle will run your notebook as usual, then generate and validate your Package which gets saved to your Notebook's output.
Your generated Package has some special logic that gets applied when it is `import`ed. If you used the Dependency Manager feature, your dependencies will be installed. We'll then `import` the submodule(s) with your code (such as `core` which comes from ＃| default_exp core) and we expose all public data members from those submodule(s) (those without a leading underscore) onto the top-level Python module; this means if you export `class Model` then you'll have `package.Model` available directly.
#### 1\. Using `kagglehub` for Kaggle resource dependencies
If your Package needs to use other Kaggle resources (Datasets, Models, Notebooks, or other Packages), you must use `kagglehub` to access them. This ensures that your package remains portable and doesn't rely on Kaggle-specific filepaths like `/kaggle/input`. Your Notebook \*must\* have all datasources attached, either through the Notebook Editor sidebar, or by executing the `kagglehub` command, before you `Save Version`, since the Save execution is not allowed to attach new datasources, or even different versions of datasources.
Example (loading a Kaggle Model):
＃| export
import kagglehub
import keras
class Model:
 def __init__(self):
 model_path = kagglehub.model_download('user/model/framework/variation')
 # OR model_download('user/model/framework/variation/version')
 self.model = keras.saving.load_model(model_path)
 def predict(self, features):
 return self.model.predict(features)
You can use the `Copy kagglehub command` option in the Notebook Editor Input sidebar to get the correct command for a given resource.
Note that there are currently some limitations on accessing older versions of Dataset, Notebook, or Package datasources, see the Known Issues section below for more details.
#### 2\. Using Dependency Manager to import Python dependencies
Kaggle Notebooks have many popular python packages pre-installed in their base Docker Image, but there's a lot of great packages not pre-installed which you may want to use. Kaggle Notebooks have a Dependency Manager tool (see [documentation](https://www.kaggle.com/discussions/product-announcements/532336)) which not only installs external python packages into your Notebook, but also saves their version so that your Notebook (or exported Package) will use that same version when re-used later. This is important for our goal of having reproducible artifacts, and also means that your Notebook (or Package) can use those dependencies in a competition scoring session where internet access is not allowed.
In the Notebook Editor menu select `Add-ons` -> `Install Dependencies` and write your `pip install ...` commands. In your Interactive Notebook Editor session, you'll need to manually `Run` from the `Dependency Manager` window to install them; this requires an active Notebook session with Internet enabled, though note that you'll have to then disable Internet if you want to submit to a competition. When you Save your Notebook, your dependencies will be installed prior to the Save execution, even if your Notebook has Internet disabled.
When your exported Package is imported elsewhere it will automatically run the Dependency Manager's installation script which installs its saved package archives.
#### 3\. Package Validation
When you Save a Notebook which exports a Package, we perform some validation on that Package. This step checks for several things:
* **Import:** Ensures that we can `import` your Package without errors.
* **Create a Model:** If your Package has a `class Model` defined, we will create an instance of it to ensure that succeeds.
* **Competition-Specific Checks (if applicable):** If your Package is intended for a code competition, we run that competition's `kaggle_evaluation.test` function with your `Model` to check whether you're following the expected input/output format.
* **Create a Model:** If your Package has a `class Model` defined, we will create an instance of it to ensure that succeeds.
* **Dependency tracking:** We track all the `kagglehub` dependencies requested by your Package during the above steps and write the versions used into `kagglehub_requirements.yaml`. This helps promote reproducibility, so that later re-use of your Package will use the same versions of those dependencies instead of silently taking newer versions which could cause breakage or altered behavior.
If validation fails, you'll see error messages in the saved Notebook's Output tab. You'll need to fix the issues and Save a new version. One common error case may be that your Notebook `import`ed a required package which worked in your Interactive session, but that `import` statement was not exported to your Package via the `nbdev` tag ＃| export.
* * *
### Importing a Package
You can import a Kaggle Package using `kagglehub.package_import()` in Kaggle Notebooks, Colab, your local machine, or anywhere you have `kagglehub` installed. See the `kagglehub` [homepage](https://github.com/Kaggle/kagglehub) for more details, including how to login with your Kaggle credentials which will be required to access private resources.
 import kagglehub
 
 # Import the package (replace with the actual handle)
 package = kagglehub.package_import('user/notebook-name') # Take latest version
 # OR take specific version
 package = kagglehub.package_import('user/notebook-name/versions/123')
 
 # Use the package, calling whatever code it had defined, for example:
 model = package.Model()
 result = model.predict(...)
#### Docker
When running Packages on your own machines, we highly recommended you use Docker. Using the correct Docker image ensures that the Package has the same system dependencies as when it was created. It also provides a sandboxed environment, isolating your code from your main system when running code which can alter your python environment by installing dependencies, or could be untrusted code altogether.
First install [Docker](https://www.docker.com/get-started/) on your machine. Then find your target Package's docker image tag in the Package's `package/__init__.py` file's `__docker_image__` metadata. For example you might find
 __docker_image__ = 'gcr.io/kaggle-images/python@sha256:abcxyz...'
Then run `docker pull gcr.io/...` (replacing with the correct tag value) to download the image to your machine. NOTE: our images are over 20 GB in size. Then run the following to create a Container and enter a shell to start working within it:
 docker run -it --rm \
 gcr.io/... \
 /bin/bash
Again make sure to replace with the correct image tag. You may consider other arguments such as:
* **`--gpus all`:** This gives the Docker Container access to your machine's GPU(s) which may be required for some Packages to work. You can also provide more fine-grained access.
* **`-v /path/on/your/host:/path/in/container:ro`:** This links a directory on your host machine to a directory within your Docker Container, for example if you want to access your own data file to pass new inputs to the Package within the Container. Note the `:ro` piece provides read-only permission to the Container, but that can be dropped to enable write permission if desired, but be careful when doing so while running potentially untrusted code.
* **`--name your-container-name`:** This provides a custom name to refer to your Container instead of an auto-generated name.
You should now have a shell session inside your Container where you can run `python` and access Packages via `kagglehub.package_import`. As mentioned above, you'll need to login to your Kaggle account to access private resources.
Note that our Docker Images are updated every few weeks, generally with only modest updates between each. In many cases a Package could still work on somewhat older or newer Images relative to the precise one on which it was saved, and you could try this rather than downloading several of our large Images separately. One caveat is we have two "branches" of Images, one for CPU sessions and one for GPU sessions, and you should take care to use the right one. See our repositories of [CPU-based Images](http://gcr.io/kaggle-images/python) and [GPU-based Images](http://gcr.io/kaggle-gpu-images/python).
#### GPUs
Packages can use GPUs for their model inference and we tag this as metadata `__gpus__ = ...` within the exported Package's `__init__.py` file. Such Packages may fail when run without GPU(s), or even without the precise GPU configuration it was created with.
* * *
### Submitting to a Package Competition
To submit to a Kaggle Code Competition that uses Packages, follow these steps:
1. **Join the Competition:** Make sure you've joined the competition.
2. **Create a Package Notebook:** Create a Kaggle Notebook that defines your Package, following the instructions in the "Creating a Package" section. Your Notebook must be attached to the competition, for example by using the `New Notebook` button on the competition's `Code` page.
3. **Follow Competition Package format:** Your Package must define a `class Model` with a `predict()` method. This method must accept the correct input type(s) and returns the correct output type(s), as specified by the competition.
4. **(Optional) Test your Package:** Use the competition's provided `kaggle_evaluation.test(Model)` function to test that your `Model` returns appropriate responses. The Package's Validation run at Save time will also run this.
5. **Save Version and Submit:** "Save Version" of your notebook. Once it's finished running and validation passes, go to the Output tab of your saved version and click `Submit to Competition`.
6. **(Shortcut) Submit from the Notebook Editor:** The Competition panel in the Editor sidebar lets you Submit directly from the Editor, which automatically combines the Save Version and Submit steps sequentially.
7. **Review Competition Documentation:** Carefully read the competition's documentation pages for any specific rules or constraints which are required of you.
Kaggle's submission system will then run a hidden scoring session where we import your Package, instantiate a `Model` instance, iterate over the competition's hidden test set and call your model's `predict` function over each test batch, then aggregate your predictions and calculate your score using the competition's evaluation metric.
Your scoring session will use the same Notebook Accelerator (GPU) which was configured in the Kaggle Notebook which generated your Package. Future improvements may decouple this.
Like any Kaggle Code Competition, we intentionally limit the information you can obtain about your scoring session to discourage exfiltration of information about the hidden test set. See more information and debugging tips [here](https://www.kaggle.com/code-competition-debugging).
* * *
### Known Issues
The following is an incomplete list of limitations with current Package functionality:
1. **Cannot reference older versions of Notebook or Package datasources:** Our Notebook Editor will allow you to attach older versions of Notebook datasources (which includes Packages) via `kagglehub.notebook_output_download('user/notebook/versions/123')` or `kagglehub.package_import('user/notebook/versions/123')` and that will work in an Interactive session. However, when you Save your Notebook we auto-attach the latest version and that `kagglehub` command will unfortunately fail.
2. **Pin via Editor UI for older versions of Dataset datasources:** The same behavior described above applies to Dataset datsources, except that we support a workaround by Pinning your datasource. Once you attach your older Dataset, you can use the right-hand sidebar to Pin it to that older version which will be honored when Saving your Notebook.
3. **Cannot reference multiple versions of Datasets or Notebooks:**Model datasources support multi-versioning, but other types currently do not.
4. **Utility Scripts not supported:**Unfortunately the `kagglehub.utility_script_install` command is not supported within a Kaggle Notebook and cannot be used in your Package. However, Packages offer (mostly) a superset of Utility Script behavior, so you may consider converting your Utility Script into a Package and importing that instead.
5. **Cannot nest a Package into itself:**You may define your Package to utilize another Package inside it (nesting), but you cannot refer to the Notebook in which you're currently working or older versions of it.
6. **All required datasources must be attached before Save:** When we execute your Notebook at Save time, you are not allowed to attach any datasource version which was not already attached, so you must make sure your Notebook has everything attached before saving. One preferred pattern is for your `class Model` to have a `def __init__(self)` constructor which retrieves all required dependencies, and you execute a (non-exported) cell with `model = Model()` (or even run the competition's `kaggle_evaluation.test` function) in your Interactive Notebook session which should run your `kagglehub` commands to pull in your required dependencies. This also lets you see if there are errors and correct them before you try to Save.
7. **`kagglehub_requirements.yaml` inference is imperfect:**We auto-generate the `package/kagglehub_requirements.yaml` file which lists all Kaggle resources which your Package requested via corresponding `kagglehub` calls, along with the version used when your Package was created. Then when your Package is imported later it tries to use those same versions again, encouraging better reproducibility for your saved Package artifact. However, the auto-generation process comes from executing your Package during the Validation Run at Save time and might not capture all possible `kagglehub` calls that your code could make. For example, if you conditionally request a resource and the Validation Run didn't trigger it, we don't know that your Package needs it. The **best practice** here is to retrieve all your resources within the top-level Package code (which gets run on `import` or within your `class Model`'s `__init__` constructor, which also gets run at Validation time.
8. **Compute settings coupled between source Notebook and exported Package:**We mark the `__gpus__` Package metadata based on the Accelerator settings of the source Notebook, and a competition Package will use those same settings for its scoring run. Ideally we'd support decoupling those, so a source Notebook can have different settings than those intended for its exported Package.
9. **Packages with Dependency Manager require Unix-like systems:**Dependency Manager currently assumes it is run on Unix-like systems (using a `.sh` script) and will not work on other platforms like Windows. We'd like to fix this, but you can also follow the guidance above on running the Package within Kaggle's Docker Image which provides a Unix-like environment.

