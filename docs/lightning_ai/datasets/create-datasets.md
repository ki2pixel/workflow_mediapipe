# Create datasets[](#create-datasets)

This section guides you through the methods for creating datasets on the Lightning platform. It highlights the use of a default Studio for datasets smaller than 400GB and a Data Prep Studio for larger datasets.

## Create small datasets[](#create-small-datasets)

To create a small dataset \(under 400GB\) simply:

  1. Start a new Studio.

  2. Download and process your data. For example, downloading the MNIST dataset.

  3. Rename the Studio to ` mnist-dataset ` .

  4. Reference this dataset from any other Studio.


https://pl-bolts-doc-images.s3.us-east-2.amazonaws.com/Docs\_Studios\_MP4/Organizing+Data-CreatingSmallDatasets.mp4

Process your data, turn off your studio, rename it as a dataset reference to use in other Studios

Use the processed dataset from a separate Studio:

https://pl-bolts-doc-images.s3.us-east-2.amazonaws.com/Docs\_Studios\_MP4/Organizing+Data-Access+Data.mp4

Access your dataset Studio from other Studios in the teamspace

Note: The default Studio includes a 400GB high-performance disk. For larger datasets, switch to a Data Prep Studio offering up to 12T storage and enhanced performance.

## Create large datasets[](#create-large-datasets)

Use the data prep Studio for datasets larger than 400GB, it offers:

  - Storage options of 3T, 8T, and up to 12T.

  - Faster data upload and download speeds

  - Faster CPUs, more cores and networking capabilities


https://pl-bolts-doc-images.s3.us-east-2.amazonaws.com/Docs\_Studios\_MP4/PrepData\_DataPrepStudio2.mp4

Data prep studios are used for processing data to use later in other Studios

## Access data via terminal[](#access-data-via-terminal)

After processing your data or creating a dataset in a Studio, follow these steps:

  1. Name your Studio according to your dataset.

  2. Turn off the Studio.


https://pl-bolts-doc-images.s3.us-east-2.amazonaws.com/Docs\_Studios\_MP4/Organizing+Data-Access+Data.mp4

Access a dataset Studio via terminal

This set up allows you to access the dataset from any Studio within your Teamspace.

## Access data via Drive[](#access-data-via-drive)

To access your data via the Drive:

  1. Navigate to the Drive.

  2. Locate the desired file or folder.

  3. Copy its path.

  4. Use the copied path in your Studio terminal for direct access.


Visit the Drive, find the file or folder you need, copy the path and use it in your Studio terminal.

https://pl-bolts-doc-images.s3.us-east-2.amazonaws.com/Docs\_Studios\_MP4/mnist\_drive\_view-2.mp4

Access a dataset Studio via teamspace Drive

