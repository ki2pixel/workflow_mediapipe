# Share datasets[](#share-datasets)

Lightning provides various options for sharing datasets whether you're aiming to collaborate within your team, across your organization, or beyond.

# Share within a teamspace[](#share-within-a-teamspace)

Explore methods to share datasets within a teamspace, ensuring smooth intra-team data access and collaboration.

## Share a Studio as dataset[](#share-a-studio-as-dataset)

Create a shared dataset by either uploading to or downloading data from a Studio. After transferring data to the Studio, deactivate it and name it as the dataset.

https://pl-bolts-doc-images.s3.us-east-2.amazonaws.com/Docs\_Studios\_MP4/mnist\_dataset.mp4

Download \(or upload\) data to a Studio. Rename your dataset Studio for easy reference.

Now access this dataset easily from any Studio within the same teamspace.

https://pl-bolts-doc-images.s3.us-east-2.amazonaws.com/Docs\_Studios\_MP4/mnist\_dataset\_access.mp4

You can access the data of one Studio from any other in the teamspace.

Please note: for training models with large datasets, [optimize the dataset](https://lightning.ai/docs/overview/optimize-data) to speed up data loading by at least 20x.

## Connect an S3 bucket[](#connect-an-s3-bucket)

Another way to share a dataset in a teamspace is to connect an S3 bucket in the teamspace.

https://pl-bolts-doc-images.s3.us-east-2.amazonaws.com/Docs\_Studios\_MP4/Docs\_Studios\_Drive\_ConnectS3Bucket.mp4

Adding a new external S3 bucket

This setup allows dataset access from any Studio in the teamspace.

https://pl-bolts-doc-images.s3.us-east-2.amazonaws.com/Docs\_Studios\_MP4/access\_s3\_connection.mp4

Access data from a connected S3 bucket

Please note: for training models with large datasets, [optimize the dataset](https://lightning.ai/docs/overview/prep-data/optimize-datasets-for-model-training-speed) to speed up data loading by at least 20x.

# Share data in an organization[](#share-data-in-an-organization)

This section shows how to seamlessly share datasets across various teamspaces within your organization.

## Export to S3 and connect[](#export-to-s3-and-connect)

Share datasets by exporting to an S3 bucket and importing them into any required teamspace.

1\. Create an AWS S3 bucket. In this example we name it ` s3-bucket-dataset-docs ` .


Create a new private S3 bucket on AWS

Select an Image

2\. Add the new S3 bucket as a data connection to your teamspace.

https://pl-bolts-doc-images.s3.us-east-2.amazonaws.com/Docs\_Studios\_MP4/add\_data\_connection.mp4

Add the private S3 bucket to the teamspace

3\. Transfer data from the Studio to the S3 bucket using [AWS CLI](https://aws.amazon.com/cli/) .

https://pl-bolts-doc-images.s3.us-east-2.amazonaws.com/Docs\_Studios\_MP4/cp\_files\_aws\_cli.mp4

Copy the data to the bucket using AWS CLI

After the transfer, access the data through the Studio terminal. The data is now within your private S3 bucket.

https://pl-bolts-doc-images.s3.us-east-2.amazonaws.com/Docs\_Studios\_MP4/check\_bucket\_data.mp4

Data from your Studio are now present in your private S3 bucket

## Publish a dataset Studio to an organization[](#publish-a-dataset-studio-to-an-organization)

Publish a [Studio as a dataset](https://lightning.ai/docs/overview/prep-data/share-datasets#studio-as-dataset) to share across your organization.

https://pl-bolts-doc-images.s3.us-east-2.amazonaws.com/Docs\_Studios\_MP4/publish\_mnist.mp4

Publish a dataset Studio to your organization's Studio templates gallery

# Export data outside Lightning[](#export-data-outside-lightning)

This section describes how to export datasets from Lightning to external platforms.

## Export to a public S3 bucket[](#export-to-a-public-s3-bucket)

Let's say you created a dataset on a Studio and want to export it outside of Lightning. To do this, first create an S3 bucket on your AWS account

1\. Let's set up an example S3 bucket named ` s3-bucket-dataset-docs ` .


Create a new public S3 bucket on AWS

Select an Image

2\. Make the bucket public.

https://pl-bolts-doc-images.s3.us-east-2.amazonaws.com/Docs\_Studios\_MP4/make\_bucket\_public.mp4

Make the S3 bucket public

3\. Add the public bucket as an S3 connection.

https://pl-bolts-doc-images.s3.us-east-2.amazonaws.com/Docs\_Studios\_MP4/add\_data\_connection.mp4

Add the public S3 bucket to the teamspace

4\. Transfer the dataset from the Studio to the S3 bucket using [AWS CLI](https://aws.amazon.com/cli/) .

https://pl-bolts-doc-images.s3.us-east-2.amazonaws.com/Docs\_Studios\_MP4/cp\_files\_aws\_cli.mp4

Copy the data to the bucket using AWS CLI

Access and use your dataset freely outside Lightning.

https://pl-bolts-doc-images.s3.us-east-2.amazonaws.com/Docs\_Studios\_MP4/check\_bucket\_data.mp4

Data from your Studio are now present in your private S3 bucket

## Publish a public Studio[](#publish-a-public-studio)

To share datasets with anyone in the world, create a [Studio as dataset](https://lightning.ai/docs/overview/prep-data/share-datasets#studio-as-dataset) and publish to the Lightning [public Studio gallery](https://lightning.ai/lightning-ai/studios?view=public§ion=featured) .

https://pl-bolts-doc-images.s3.us-east-2.amazonaws.com/Docs\_Studios\_MP4/publish\_studio.mp4

Publish the Studio to the Lightning community Studio templates gallery

