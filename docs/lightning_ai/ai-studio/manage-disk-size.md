# Manage disk size[](#manage-disk-size)

This guide outlines how to manage your Studio's disk size to optimize its performance. For more insights on data preparation read our [in-depth guide](https://lightning.ai/docs/overview/data-overview) .

## Upgrade disk space[](#upgrade-disk-space)

Studios come with a * *400GB high-performance disk ** by default. To expand disk space and upgrade network speeds use a Data Prep Studio. Data Prep Studios offer disk sizes of * *3TB, 8TB, or 12TB * *. However, keep in mind that downgrading from a Data Prep Studio isn't possible if the disk holds more than 300GB of data.

https://pl-bolts-doc-images.s3.us-east-2.amazonaws.com/Docs\_Studios\_MP4/Studio\_DiskSize\_AddDiskSpace.mp4

Use our default Studio's 400GB disk or switch to a data prep Studio for 3TB, 8TB and 12TB.

## Decrease Disk Space[](#decrease-disk-space)

For those who have upgraded and have less than 300GB on their disk, downgrading is a straightforward process. If your disk contains more than 300GB, you must first reduce your data to less than 300GB to switch machines.

## Use Studio as a dataset[](#use-studio-as-a-dataset)

When dealing with large datasets, finish preparing your data in a Studio, name it as the dataset and put it to sleep. This dataset can be accessed by any other Studio in the teamspace.

Performing high-demand tasks like training in a dataset Studio can lead to slow operations. It's recommended to use separate Studios for dataset management and your main work.

