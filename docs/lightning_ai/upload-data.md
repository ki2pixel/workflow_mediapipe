# Upload data[](#upload-data)

Manual data uploads can be slow and error-prone, especially at scale. Lightning simplifies this with flexible upload options—web UI, CLI, and SDK—enabling fast, automated, and consistent data transfers. This reduces setup time and lets users access their data immediately within Studio, speeding up iteration.

## Upload via web app[](#upload-via-web-app)

Use the Lightning Drive to upload, view and manage datasets and files.

https://pl-bolts-doc-images.s3.us-east-2.amazonaws.com/Docs\_Studios\_MP4/Docs\_PrepData\_UploadData2.mp4

Uploading data via web app

Note: the following code was used to create 200 files with a size ranging from 1MB to 100MB for the recording above.

`1 2 3 4 5 6 7 8 ` ` import os os.makedirs('./demo', exist_ok=True) os.chdir('./demo') for i in range(1, 1000): os.system(f"truncate -s {i}KB {i}.bin")`

## Upload programmatically[](#upload-programmatically)

For programmatic uploads, use the Lightning SDK:

https://pl-bolts-doc-images.s3.us-east-2.amazonaws.com/Docs\_Studios\_MP4/Docs\_PrepData\_UploadData\_SDK.mp4

Upload data via SDK

With ` studio.upload_file(path_to_local_file, path_to_remote_file) ` you can upload files. This allows for programmatic filtering or parallelizing uploads. A full example is:

`1 2 3 4 5 6 7 8 9 10 11 12 13 ` ` #! pip install lightning_sdk # LIGHTNING_USER_ID=000000-000000-000000-00000-000000000 # LIGHTNING_API_KEY=111111-111111-111111-11111-111111111 import os from lightning_sdk import Studio studio = Studio(name="my-studio-name", teamspace="my-teamspace", user="my-user") total_root = "path/to/demo" for root, _, files in os.walk(total_root): for f in files: # upload in remote dir where everything will be relative to home remote_path = os.path.join(os.path.relpath(root, total_root), f) studio.upload_file(os.path.join(root, f), remote_path) `

Here, the code iterates over all files in the demo path \(directories will be created on the fly if necessary\). When uploading a file, the remote path is always relative to the home directory and must be a subdirectory of it. By specifying the ` remote_path ` as ` os.path.join(os.path.relpath(root, total_root), f) ` , every file will be uploaded to the path relative to the root of the path we want to upload under the Studio's home directory.

## Upload via CLI[](#upload-via-cli)

Uploading data programmatically often requires writing custom scripts, which adds unnecessary overhead for simple tasks. The Lightning CLI removes that friction by enabling fast, script-free uploads directly from the terminal. This streamlines workflows and makes it easy to move data into Studio with a single command.

To install the CLI run:
`pip install --upgrade lightning-sdk`


Upload data with the following command:
`lightning upload <folder> --studio <teamspace/studio_name>`


https://pl-bolts-doc-images.s3.us-east-2.amazonaws.com/Docs\_Studios\_MP4/Docs\_PrepData\_UseData.mp4

Upload using Lightning CLI

## Upload data to new Studio[](#upload-data-to-new-studio)

Creating new environments often involves multiple setup steps and manual data transfers. This slows down onboarding and experimentation. With ` lightning open ` CLI command, we can instantly upload local data and launch a new Studio in the browser. This streamlines setup into a single command, enabling faster project starts and reducing friction.

Unlike ` lightning upload ` , which sends data to an existing Studio, ` lightning open ` uploads local data and launches a new Studio in one step.

To install the CLI run:
`pip install --upgrade lightning-sdk`

Open the local data in a new Studio with the following command:
`lightning open [PATH] `

https://pl-bolts-doc-images.s3.us-east-2.amazonaws.com/lightning+open.mp4

Upload data and open Studio

## Access the data[](#access-the-data)

Access the data via the Studio terminal or in your scripts.

https://pl-bolts-doc-images.s3.us-east-2.amazonaws.com/Docs\_Studios\_MP4/Docs\_PrepData\_UploadData\_AccesstheData2.mp4

Accessing data

