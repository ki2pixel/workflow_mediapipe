# Virtual machines \(VM\)[](#virtual-machines-vm)

For purists who " * *just want a VM with ssh access ** ", there are two ways to achieve that - via the web-based dashboard or via CLI

## Create account[](#create-account)

First, [login and create a free account](https://lightning.ai/sign-up) .

Tip: Use a work or university email for instant verification. Otherwise you will be put on a waitlist. * *We process sign up requests within 48 hours. ** Lightning is not available in every country, yet. If your country is not available, we might already be working on launching there so follow us on Twitter to stay in the loop.

https://pl-bolts-doc-images.s3.us-east-2.amazonaws.com/Docs\_Studios\_MP4/Overview\_CreateAccount2.mp4

Click on "Start free" to sign up for a Lightning account.

## Start instance[](#start-instance)

The first time you login, you'll land on a running instance with a web-based browser. You don't need to use the website to use the VM. Simply click the "connect via ssh" icon on the top right and close the browser.

https://pl-bolts-doc-images.s3.us-east-2.amazonaws.com/Docs\_Studios\_MP4/Docs\_Studios\_SSHAccess2.mp4

Select "Connect via SSH" and follow instructions to set up SSH in terminal.

## Manage with CLI[](#manage-with-cli)

If you prefer to do everything via CLI, here are all the commands you need to start a new VM.

First, install the CLI

`1 ` ` pip install lightning-sdk -U`

Here are all the commands you need \( [full CLI docs here](https://lightning.ai/docs/overview/build-with-studios/cli) \).

Basics

basic commands to view, create and ssh

Persistent

Start/stop your VM with full data persistence

Switch GPU

VMs can switch the GPUs dynamically

`1 2 3 4 5 6 7 8 ` ` lightning vm list lightning vm create lightning vm ssh  lightning vm start lightning vm stop  lightning vm switch --machine A100`

## Upload data[](#upload-data)

You can upload data via the web UI \(visit the Teamspace/Drive\), or via the CLI.

Files

Upload/download files

Folders

Upload/download folders

`1 2 3 4 5 ` ` lightning upload file /path/to/local/file.txt -s myteam/mystudio lightning download file path/to/studio/file.txt --studio myteamspace/mystudio  lightning upload folder /path/to/local/folder -s myteam/mystudio -r /projects/data lightning download folder projects/data --studio myteamspace/mystudio --local-path ./local_dir`

## Connect data[](#connect-data)

Bring data from S3/GCP, etc... by connecting it to the VM.

[Read more here.](https://lightning.ai/docs/overview/organize-data)

