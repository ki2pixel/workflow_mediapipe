# CLI[](#cli)

Create and manage Studios \(ie: "VMs"\) via the CLI.

## Installation[](#installation)

To use the Lightning CLI, first install the Lightning SDK:

`1 ` ` pip install lightning-sdk -U`

## Basic Usage[](#basic-usage)

CLI commands follow the syntax

`1 ` ` lightning [command]`

Get help on possible commands by running

`1 ` ` lightning COMMAND --help`

## Authentication[](#authentication)

Authentication persists across sessions. Log in to use the CLI commands by running ` lightning login ` and entering your credentials in the browser tab that opens.

## Create Studio[](#create-studio)

Create new Studios from the terminal by running

`1 2 3 ` ` lightning studio create --teamspace <OWNER/TEAMSPACE_NAME> --name <STUDIO_NAME> `

Both ` --name ` and ` --teamspace ` are optional. In case --name is not specified, the Studio will be named randomly and in case --teamspace is not specified, it will ask interactively which teamspace to use \(or take it from the config if specified\).

## Start Studio[](#start-studio)

Start an already existing Studio with

`1 ` ` lightning studio start --name <STUDIO_NAME> --teamspace <OWNER_NAME>/<TEAMSPACE_NAME> --machine T4`

Similar to Studio creation ` --name ` and ` --teamspace ` are optional, where it will ask for both of them if not specified as arguments or in the config file.

## Stop Studio[](#stop-studio)

Stop a running Studio with:

`1 ` ` lightning studio stop --name <STUDIO_NAME> --teamspace <OWNER_NAME>/<TEAMSPACE_NAME>`

When omitting ` --name ` and/or ` --teamspace ` , the CLI will prompt for them if it cannot resolve them from the environment.

## Switch Studio Machine[](#switch-studio-machine)

Switching already running Studios to a different machine, can be achieved with:

`1 ` ` lightning studio switch --name <STUDIO_NAME> --teamspace <OWNER_NAME>/<TEAMSPACE_NAME> --machine H100`

## Upload local files to Studio[](#upload-local-files-to-studio)

Upload files or folders from your local workspace to a selected Studio. Studios do not need to be running to use this operation. Note that folders needs the recursive flag \(i.e. ` lightning studio cp -r ` \)

`1 2 3 ` ` lightning studio cp [LOCAL_PATH] [STUDIO_PATH] lightning studio cp -r [LOCAL_PATH] [STUDIO_PATH]`

* *Arguments and Flags **

  - ` LOCAL_PATH ` \(Required/str\): The path local file or folder to upload

  - ` STUDIO_PATH ` \(Required/str\): The path to the file or folder within the Studio. Format: ` lit://{org/user}/{teamspace_name}/studios/{studio_name}/{studio_path}` ``

  - ` -r ` or ` --recursive ` \(Required for folders\): Must be specified when uploading folders


* *Examples **

Upload a file to a specific studio:

To upload ` main.py ` from your Studio named ` my-studio ` in your user teamspace \(username: ` user-123, ` not an organization teamspace\) ` default-teamspace ` , use the following command:

`1 ` ` lightning studio cp ./main.py lit://user-123/default-teamspace/studios/my-studio/local_main.py`

Upload a directory to a specific location in a studio:

To upload a folder ` ./tests/ ` from your Studio named ` my-studio ` in your user teamspace \(username: ` user-123, ` not an organization teamspace\) ` default-teamspace ` , use the following command:

`1 ` ` lightning studio cp -r ./tests/ lit://user-123/default-teamspace/studios/my-studio/local_tests/`

## Download studio files[](#download-studio-files)

Download files and folders to your local workspace from studios. Studios do not need to be running to use this operation. Note that folders needs the recursive flag \(i.e. ` lightning studio cp -r ` \)

`1 2 3 ` ` lightning studio cp [STUDIO_PATH] [LOCAL_PATH] lightning studio cp -r [STUDIO_PATH] [LOCAL_PATH]`

* *Arguments and flags **

  - ` STUDIO_PATH ` \(Required/str\): The path to the file within the Studio. Format: ` lit://{org/user}/{teamspace_name}/studios/{studio_name}/{studio_path}`

  - ` LOCAL_PATH ` \(Required/str\): The path locally where files will be downloaded to

  - ` -r ` or ` --recursive ` \(Required for folders\): Must be specified when downloading folders


* *Examples **

Download a file from a specific studio:

To download ` main.py ` from your Studio named ` my-studio ` in your user teamspace \(username: ` user-123, ` not an organization teamspace\) ` default-teamspace ` , use the following command:

`1 ` ` lightning studio cp lit://user-123/default-teamspace/studios/my-studio/main.py ./studio_main.py`

Download a directory to a specific local location:

To download folder ~/tests/ from your Studio named ` my-studio ` in your user teamspace \(username: ` user-123, ` not an organization teamspace\) ` default-teamspace ` , use the following command:

`1 ` ` lightning studio cp -r lit://user-123/default-teamspace/studios/my-studio/tests/ ./`

_Note: you can not download files from an s3 connection_

Download the entire studio:

`1 ` ` lightning studio cp -r lit://user-123/default-teamspace/studios/my-studio/ ./`

## List Studios[](#list-studios)

Listing existing studios can be done with

`1 ` ` lightning studio list`

## Accessing Studio via SSH[](#accessing-studio-via-ssh)

To access Studios via SSH run:

`1 ` ` lightning studio ssh --teamspace <OWNER/TEAMSPACE_NAME> --name <STUDIO_NAME>`

This will directly open a shell in the specified Studio. As with all other commands, the ` --name ` and ` --teamspace ` flags are optional and will be prompted for if not specified but required for Studio resolution.

