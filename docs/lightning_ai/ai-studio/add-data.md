# Add data[](#add-data)

Lightning Drive is a unified cloud filesystem shared by all users in a Teamspace. It allows every type of workload - Studios, Jobs, Deployments, Pipelines, etc... - to share a single, unified filesystem that can be accessed by any workload.

Think of a teamspace Drive like a _permissioned_ Google drive folder \(or data lake\) for any type of file \(ie: unstructured object store\).


The Lightning Drive

Select an Image

Use the Drive to:

  - Share and host files

  - Connect S3 buckets

  - Upload data

  - Visualize data


# Key concepts[](#key-concepts)

## Shared by all Studios[](#shared-by-all-studios)

All Studios in a teamspace share the same drive. This means any Studio can access the files of the other Studios.


A terminal showing access to other Studios and their associated files.

Select an Image

The shared filesystem drastically simplifies complex ML workflows on Lightning. To illustrate, try the following examples:

  - Train a model on Studio A, access the checkpoints from Studio B.

  - Train a model on Studio A, explore the artifacts as it trains from Studio B.

  - Label data on Studio A, explore the labels on Studio B.


The first 10GB are free for all users. Each tier is subject to a different total limit of data that can be stored in the Drive.

  - Free: 50 GB total storage limit \(only first 10 GB free\)


  - Pro: 200 GB total storage limit \(only first 10 GB free\)


  - Teams: 2 TB total storage limit \(only first 10 GB free\)


  - Enterprise: Unlimited storage


## One Drive per teamspace[](#one-drive-per-teamspace)

Each teamspace has a single isolated drive. Use this to control access to data.


Each teamspace has its own team members, data access, and budgets.

Select an Image

Let's say you have dataset A that can only be accessed by the data team and dataset B that can only be accessed by the research team. The Drive gives you that ability natively.


Teamspaces natively allow for data access control.

Select an Image

Let's say you want to give data access to someone outside your organization. Add them as a guest to the teamspace and they'll only be able to access the data in that teamspace.


Invite members to your teamspace.

Select an Image

## Job files[](#job-files)

Studios can run jobs async using the same environment and files of the Studio. For example, set up a Studio to finetune a model and then submit 10 jobs to finetune the model under 10 different conditions at once.


A list of 10 jobs running to finetune a model.

Select an Image

Once the jobs have completed, access the job files from the terminal. You can either copy those files to the Studio or reference them directly.


Use the terminal to access files from any job.

Select an Image

## Navigate the Drive[](#navigate-the-drive)

If you know how to browse files on your laptop, you know how to use the Drive.

Use the Drive like you use the file browser on your laptop. Move around with your keyboard, press the space bar to preview files, or double click to open them in standalone windows.

## Delete files[](#delete-files)

To delete files on a granular level from the Drive, navigate to any file or folder, hover over it, and select the 3-dots context menu.


Hover over a folder and select the 3-dots context menu to reveal the Delete option.

Select an Image

# Import data[](#import-data)

## Upload data[](#upload-data)

Drag and drop files and folders into the drive to upload data.


https://pl-bolts-doc-images.s3.us-east-2.amazonaws.com/Docs\_Studios\_MP4/Docs\_Studios\_Drive\_DragandDrop.mp4

How to upload data to your drive.

To upload data programmatically, use the lightning SDK.

## Upload via SDK[](#upload-via-sdk)

Upload files or folders from your local workspace to a selected Studio. Studios do not need to be running to use this operation.

`1 ` ` lightning upload PATH [flags/optional arguments]`

### Arguments and flags[](#arguments-and-flags)

  - ` PATH, -p, --path ` \(Required/str\): The path to the file or directory you want to upload.

  - ` -s, --studio ` \(Optional/str\): The name of the studio to upload to. If not specified, a selection menu will be shown. Format: ` <TEAMSPACE-NAME>/<STUDIO-NAME>`

  - ` -r, --remote_path ` \(Optional/str\): The path where the uploaded file should appear in your Studio. Must be within your Studio's home directory and will be relative to that. If not specified, it will use the file or directory name of the path you want to upload and place it in your home directory.


### Examples[](#examples)

Upload a file to a specific studio:

`1 ` ` lightning upload /path/to/local/file.txt -s myteam/mystudio`

Upload a directory to a specific location in a studio:

`1 ` ` lightning upload /path/to/local/folder -s myteam/mystudio -r /projects/data`

## Connect S3 buckets[](#connect-s3-buckets)

It takes <1 minute to connect an S3 bucket. Click "Add data" on the top right, select S3 bucket and follow the instructions.

https://pl-bolts-doc-images.s3.us-east-2.amazonaws.com/Docs\_Studios\_MP4/Docs\_Studios\_Drive\_ConnectS3Bucket.mp4

How to connect S3 buckets to your Studio.

An S3 connection is only available to the teamspace; this is to give you the ability to isolate your data as needed.

Feel free to connect multiple S3 buckets. There is no size limit to how much data you can connect.

## Supported file types[](#supported-file-types)

We built the Drive for high-performance AI workflows \(model training, serving, data prep, etc...\). Thus all file types are supported.


Drive supports all file types.

Select an Image

## Add connectors \(Snowflake, etc.\)[](#add-connectors-snowflake-etc)

Lightning Drive can connect to any type of data service. If you need a connector, please [get in touch](https://discord.gg/MWAEvnC5fU) * *.**

# Download data[](#download-data)

This section describes various methods to download data from Studios.

## Via Drive[](#via-drive)

Hover over the folder or item you'd like to download, select the more actions UI element, then select download.

https://pl-bolts-doc-images.s3.us-east-2.amazonaws.com/Docs\_Studios\_MP4/Docs\_Studios\_Drive\_DownloadData\_ViaDrive.mp4

Download any item in the teamspace via the Studio drive.

## Via VSCode[](#via-vscode)

Right-click the file or folder in VSCode and click "download".

https://pl-bolts-doc-images.s3.us-east-2.amazonaws.com/Docs\_Studios\_MP4/Docs\_Studios\_Drive\_DownloadData\_ViaVSCode2.mp4

Download from the VSCode screen in Studio by right-clicking on an item in the Studio.

## Via SDK[](#via-sdk)

Use simple Python code to get files onto a local machine.

Download a file from the Teamspace Drive:

`1 2 3 4 5 ` ` from lightning_sdk import Teamspace t = Teamspace(name="model-xy", org="acme-ai") t.download_file("train_model_x.py", file_path="/teamspace/studios/this_studio/train_x.py") t.download_file("train_model_y.py")`

Download a file from a Studio:

https://pl-bolts-doc-images.s3.us-east-2.amazonaws.com/Docs\_Studios\_MP4/Docs\_Studios\_Drive\_DownloadData\_ViaLightningSDK.mp4

Use Lightning SDK to download from the studio.

## Via CLI[](#via-cli)

Use the download command to get files onto a local machine.


Copy the download command for a studio's file or folder from your drive.

Select an Image

# Billing[](#billing)

Most platforms make it hard to discover what you're getting billed for and even harder to manage it. With Lightning you'll have a convenient interface designed around our infrastructure admins needs and a single "all-in price" to make it easier to manage the most valuable resource in AI, your data.

The first 10 GB of data you save on the Drive are free. After that, they are billed at $0.10 / GB / month. This includes the raw storage as well as the cross-region IOPS that you'd typically pay for when you go direct to other platforms.

_Note: data connections that you own are not billed. If you choose to deploy to your own VPC, Lightning will not bill you for data as this will all live within your cloud account\(s\). _

## Cost[](#cost)

Add row above

Add row below

Delete row

Add column to left

Add column to right

Delete column

* *Resource type **

* *Description **

* *Price **

Data uploads

Lightning's managed data solution which is great for getting started and prototyping.

$0.10 / GB / month

EFS

AWS's high performance file system. Perfect for when you need high-speed read and write.

Storage: $0.0125 per GB/day, Read: $0.0375/GB, Write: $0.075/GB

Google Filestore

GCP's high performance file system. Perfect for when you need high-speed read and write.

$0.5625 / GB / month

Cloud agnostic storage

Lightning's managed data solution for agnostic storage across the neo-cloud providers \(e.g. Nebius, Lambda Labs, Voltage Park\)

$0.10 / GB / month

S3 and GCS connections

AWS or GCP buckets that are owned by you and want to connect to the Lightning platform.

_Unbilled_

## Org management[](#org-management)

To manage storage within an organization navigate to * *_Organization Settings > Storage_. **


Click on Storage option in the dropdown

Select an Image

Manage your storage all from one easy to use dashboard.


View all teamspaces and a breakdown of the storage

Select an Image

Click on a Teamspace to see a more granular view. Here you can navigate by data type.


Navigate by data type within the Storage settings

Select an Image

Delete one or multiple files in the list.


Deleting multiple files

Select an Image

Certain file types, like Studios, may take a minute to delete.

## Personal account management[](#personal-account-management)


Navigate to Settings tab to access account management.

Select an Image

Next click on storage option to the left, under activity. From here you can manage storage assets. Some storage will be deleted immediately while others may take time clear up.


Deleting files from storage.

Select an Image

# FAQs[](#faqs)

* *How many S3 buckets can I connect? **

  - There is no limit.


* *What is the storage limit of the Drive? **

  - The Drive itself has no limit, however depending on which tier your account is on you will have tier-based limits.


* *Do you support Snowflake, Databricks, XYZ data service? **

  - Custom connectors for any data service are available to enterprise customers.


* *What file types do you support? **

  - All file types are supported \(.mp4, .py, .obj, .mov, etc...\). Deep learning data comes in all forms, shapes, and sizes.


* *How do I optimize data loading for fast training or inference? **

  - Use the Studio data prep app to format the data in a way that gives you at least 20× speed ups for model training and serving.


* *How does the Drive work underneath? **

  - We wrote a proprietary distributed filesystem optimized for deep learning scale. The details of how this works are part of the Lightning secret sauce :\).


* *How can I add _"Other AWS accounts"_ in KMS for adding an encrypted S3 bucket * ***? * ***\(Enterprise only\) **

On the AWS console in KMS, select  _"Customer-managed keys"_ from the sidebar. Select your key then ensure you are on the _"Key policy"_ tab and you should see a section labelled _"Other AWS Accounts"_.

If you do not see the section it means you are in _policy view,_ which will display the policy as JSON. Instead you should ensure you have the following statements in the policy, replacing the account numbers \(blanked out with xxxxxxxxxxxx below\) with the one referenced on Studio Drive when adding a KMS key.

`1 2 3 4 5 6 7 8 9 10 11 12 13 14 15 16 17 18 19 20 21 22 23 24 25 26 27 28 29 30 31 32 33 34 35 36 37 38 39 ` ` [ { "Sid": "Allow use of the key", "Effect": "Allow", "Principal": { "AWS": [ "arn:aws:iam::xxxxxxxxxxxx:root" ] }, "Action": [ "kms:Encrypt", "kms:Decrypt", "kms:ReEncrypt *", "kms:GenerateDataKey *", "kms:DescribeKey" ], "Resource": " *" }, { "Sid": "Allow attachment of persistent resources", "Effect": "Allow", "Principal": { "AWS": [ "arn:aws:iam::xxxxxxxxxxxx:root", ] }, "Action": [ "kms:CreateGrant", "kms:ListGrants", "kms:RevokeGrant" ], "Resource": " *", "Condition": { "Bool": { "kms:GrantIsForAWSResource": "true" } } } ]`

