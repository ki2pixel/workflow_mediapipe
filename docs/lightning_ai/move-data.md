# Move data[](#move-data)

\(This documentation pertains to studios and Lightning managed cloud * *folders * *. For user cloud bucket * *connections ** see "Connect S3 buckets" documentation\)

The Lightning Drive makes it easy to move data between Studios, cloud buckets, and high-performance storage. Just start a Studio that has access to both the source and destination and use standard copy \( ` cp ` \) or move \( ` mv ` \) commands - just like on a local machine.

`1 ` ` cp -R /teamspace/s3_folders/my_s3_folder /teamspace/efs_folders/my_efs_folder`

# Move data across Studios[](#move-data-across-studios)

To move data from one Studio to another, run the command from the target Studio \(the one you're moving the data to\).

`1 ` ` cp -R /teamspace/studios/studio_a/my_data /teamspace/studios/studio_b/my_copied_data `

# Move data on AWS[](#move-data-on-aws)

## Studio to S3 [](#studio-to-s3andnbsp)

Copy files from a Studio into a Lightning-managed S3 folder:

`1 ` ` cp -R /teamspace/studios/my_studio_folder /teamspace/s3_folders/my_s3_folder`

## S3 to S3[](#s3-to-s3)

Move or copy files between two S3 folders:

`1 ` ` cp -R /teamspace/s3_folders/source_s3 /teamspace/s3_folders/destination_s3`

## S3 to EFS[](#s3-to-efs)

Transfer data from an S3 folder to an EFS folder:

`1 ` ` cp -R /teamspace/s3_folders/my_s3_folder /teamspace/efs_folders/my_efs_folder`

Transfer data from EFS back to S3:

`1 ` ` cp -R /teamspace/efs_folders/my_efs_folder /teamspace/s3_folders/my_s3_folder`

Move or copy files between two EFS folders:

`1 ` ` cp -R /teamspace/efs_folders/source_efs /teamspace/efs_folders/destination_efs`

# Move data on GCP[](#move-data-on-gcp)

## Studio to GCS[](#studio-to-gcs)

Copy files from a Studio to a Lightning-managed GCS folder:

`1 ` ` cp -R /teamspace/studios/my_studio_folder /teamspace/gcs_folders/my_gcs_folder`

## GCS to GCS[](#gcs-to-gcs)

Move or copy files between GCS folders:

`1 ` ` cp -R /teamspace/gcs_folders/source_gcs /teamspace/gcs_folders/destination_gcs`

## GCS to filestore[](#gcs-to-filestore)

Transfer data from GCS to high-performance Filestore:

`1 ` ` cp -R /teamspace/gcs_folders/my_gcs_folder /teamspace/filestore_folders/my_filestore_folder`

Copy files from Filestore back to GCS:

`1 ` ` cp -R /teamspace/filestore_folders/my_filestore_folder /teamspace/gcs_folders/my_gcs_folder`

Move files between Filestore folders:

`1 ` ` cp -R /teamspace/filestore_folders/source /teamspace/filestore_folders/destination`

Copy files from a connected external GCS bucket to a Filestore folder:

`1 ` ` cp -R /teamspace/gcs_connections/my_bucket /teamspace/filestore_folders/my_filestore_folder`

