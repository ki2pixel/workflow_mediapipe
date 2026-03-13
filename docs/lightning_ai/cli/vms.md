# VMs[](#vms)

The Lightning SDK provides programmatic control for the VM. Use this to interact with the VM programmatically.

Within a VM, use the SDK to programmatically control the VM itself \(switching machines etc.\).

Outside a VM, use the SDK to integrate VM into ML pipelines, CI/CD, production workflows, and more.

## Install the SDK[](#install-the-sdk)

The SDK is automatically installed inside the VM.

To install the SDK outside of a VM \(on your local, or a CI/CD system\) run this command:

`1 ` ` pip install lightning-sdk `

Once the SDK is installed, you'll now have full programmatic control over all your VM on the Lightning platform.

## Basic objects[](#basic-objects)

The SDK follows principles you know from interacting with a VM through your browser. It is implemented in object-oriented Python and has ` User ` , ` Organization ` , ` Teamspace ` and ` VM ` classes.

`1 2 3 4 5 6 7 8 9 10 11 12 13 ` ` from lightning_sdk import VM, Teamspace, User, Organization # allows interaction with the VM named "my-vm" in the Teamspace "train-model" of user "zeus" s = VM(name="my-vm", teamspace="train-model", user="zeus") # allows interaction with Teamspace "train-model" of organization "olymp" t = Teamspace("train-model", org="olymp") # allows interaction with user "zeus" u = User("zeus") # allows interaction with organization "olymp" o = Organization("olymp")`

If you are accessing a VM in an _organizational _Teamspace rather than a user \(personal\) Teamspace, be sure to specify the ` org ` .

`1 ` ` s = VM(name="my-vm", teamspace="train-model", org="my-company-org")`

## Get started[](#get-started)

Exploring the SDK in a VM is the easiest as you are already authenticated, and all the relevant environment variables are exported.

To get started on your laptop, you need to export two environment variables: ` LIGHTNING_USER_ID ` and ` LIGHTNING_API_KEY ` , both of which you can find in the "Global Settings" if you click on your profile icon on the top right. In the appearing Menu, select "Keys" on the left-hand side, and you will see the values for your unique set of keys under "Programmatic access" labeled as "Login via CLI". Export those variables in your terminal and you are good to go.

https://pl-bolts-doc-images.s3.us-east-2.amazonaws.com/Docs\_Studios\_MP4/Docs\_Studios\_SDK\_GettingStarted.mp4

Keys are in your global settings

## Class construction[](#class-construction)

You need to initialize the corresponding classes to use specific parts of the SDK. For example, when interacting with a VM, you need to initialize the ` VM ` class. Every class has several optional arguments and some environment variables that will be picked up if those arguments are not specified.

Example initializing a VM

`1 2 3 4 5 6 7 8 9 10 11 12 13 ` ` #! pip install lightning-sdk # export the following variables for authentication (use your own ID and API key) # LIGHTNING_USER_ID=000000-000000-000000-00000-000000000 # LIGHTNING_API_KEY=111111-111111-111111-11111-111111111  from lightning_sdk import VM # this picks up name, teamspace and owner from environment variables. # running this within a VM allows you to manage the VM you're in. s = VM() # this allows remote control of a VM from outside # replace name, teamspace and user/org with your own information remote_control = VM(name="my-vm", teamspace="my-teamspace", user="my-user")`

To initialize a VM, you could do ` VM(name="my-vm", teamspace="my-teamspace", user="my-user") ` or you could just do ` VM() ` if you have the correct environment variables exported. Inside a VM these always point to the current VM so that ` VM() ` will always give you programmatic control over your current VM. Same goes for ` Teamspace() ` , ` User() ` and ` Organization() ` : They always point to the current scope.

You can also only specify some of these variables and, provided you exported the related environment variables, the other ones will be picked out automatically. So ` VM(name="some-other-vm") ` would point to another VM in the same Teamspace within the same User/Organization.

Add row above

Add row below

Delete row

Add column to left

Add column to right

Delete column

VM ID

`LIGHTNING_CLOUD_SPACE_ID`

Teamspace Name

`LIGHTNING_TEAMSPACE`

User Name

`LIGHTNING_USERNAME`

Organization Name

`LIGHTNING_ORG`

For the sake of readability, in this documentation, we will use the empty constructors, but you could also pass the respective arguments instead.

## Start, stop and delete a VM[](#start-stop-and-delete-a-vm)

After construction with ` vm = VM() ` , we can start, stop and delete it with simple calls to ` vm.start() ` , ` vm.stop() ` and ` vm.delete() ` . That means that after initializing your VM, it is not automatically starting. You have to explicitly start it with ` vm.start() ` . While auto-shutdown works on VM started through the SDK as well, these VM will be kept alive as long as you have a Python object referencing.

While ` vm.stop() ` gently shuts down your VM until you decide to spin it up again, ` vm.delete() ` is a destructive action that also deletes the VM and all your files from that VM, so you won't be able to use it again.

Example stopping a running VM \(caution: when running this from within a VM, you will have to restart it to continue exploring\):

`1 2 3 4 5 6 7 8 9 10 11 12 13 14 15 16 17 18 19 ` ` #! pip install lightning-sdk from lightning_sdk import VM # run from inside a VM: control the vm you are running on s = VM() s.stop() # create a new VM in same Teamspace s = VM(name="start-stop-delete-demo", create_ok=True) # before we call start, the VM exists but isn't running s.start() # now let's stop the VM s.stop() # and finally, delete it to leave no traces. s.delete() `

## Switch machines[](#switch-machines)

The SDK has a built-in enum for different machine types. Switching machines with this enum is as easy as running ` vm.switch_machine(Machine.T4) ` or whatever other type of machine you want to use. In contrast to the browser-based interface, the SDK actually blocks until the new machine is ready, as it would be unsafe to continue using the machine otherwise.

Example switching machines using the SDK:

`1 2 3 4 5 6 7 8 ` ` #! pip install lightning-sdk from lightning_sdk import VM, Machine # run from inside a VM: control the vm you are running on s = VM() # the VM is already running since we're running from within the VM - no need to start it s.switch_machine(Machine.T4)`

Another option is that, unlike through the browser, you can start VM on a specific machine via the SDK. Just pass the machine type to the ` start ` method like so: ` vm.start(Machine.T4) ` .

`1 2 3 4 5 6 7 8 9 10 11 ` ` #! pip install lightning-sdk from lightning_sdk import VM, Machine # run from inside a VM: create a VM in the same Teamspace s = VM(name="start-on-machine-demo") # start the VM directly on an T4 instead of first going to a CPU-4 s.start(machine.T4) # delete the VM to leave no traces s.delete() `

* *Note: ** this only works if your VM wasn't already running.

## Run Commands[](#run-commands)

To run commands, the SDK provides you with two options:

  1. Using ` vm.run("my fancy command") ` , the VM will execute the command and return the output. If your command doesn't succeed \(e.g. returns a nonzero exit code\) this method will raise an error.

  2. The ` vm.run_with_exit_code("my fancy command") ` will also run the command but instead of raising and error on failure, it will always return the exit code alongside the output for you to handle it manually.


Example comparing the two mechanisms to run things:

`1 2 3 4 5 6 7 8 9 10 11 12 13 14 15 16 17 18 19 20 21 22 23 24 25 26 27 28 29 30 31 32 33 ` ` #! pip install lightning-sdk from lightning_sdk import VM # run from within a VM: control the VM you're in s = VM() # run a command and don't care for specific exit-codes.  output = s.run("echo hello") assert output == "hello" # run a command that fails try: output = s.run("echo failed; exit 5") # we know this won't happen since we explicitly exited with 5 print(output) except RuntimeError: # now we can do error handling print("an error occurred") # get output and exit_code separately output, exit_code = s.run_with_exit_code("echo hello; exit 5") assert output == hello # allows for error-handling depending on specific exit-codes if exit_code == 0: # we know this won't happen since we explicitly exited with 5 print("command ran successfully") elif exit_code == 5: # this could be a specific error case to catch print("expected manual exit code") else: # we only expect 0 or 5 as valid exit-codes here print("an error occurred", output) `

## Enable/disable autosleep[](#enabledisable-autosleep)

To directly enable autosleep from the SDK:

`1 2 3 4 5 6 7 8 9 ` ` from lightning_sdk import VM s = VM() # Disable auto-sleep s.auto_sleep = False # Re-enable auto-sleep s.auto_sleep = True`

# API Reference[](#api-reference)

## VM[](#vm)

`1 2 3 4 5 6 ` ` from lightning_sdk import VM vm = VM(name='my-vm-name', teamspace='my-teamspace', org='my-org') vm.start() vm.stop() duplicated_vm = vm.duplicate()`

A VM object has the following functions:

  - ` * *init ** ` : creation of VM

    - ` name (Optional[str]) ` : the name of the VM

    - ` teamspace (Optional[Union[Teamspace, str]]) ` : the teamspace the VM is contained by

    - ` org (Optional[Union[str, Organization]]) ` : the organization owning the teamspace

    - ` user (Optional[Union[str, User]]) ` : the user owning the teamspace, Note: Since a teamspace can either be owned by an org or by a user directly, only one of the arguments can be provided.

  - ` start ` : start a VM

    - ` machine (Machine) ` : the machine to start a VM on, default: CPU-4

    - ` interruptible (bool) ` : starts the VM on a interruptible instance. Note that this means the VM can be terminated at any point in time.

  - ` stop ` : stop a running VM

  - ` delete ` : delete an existing VM

  - ` duplicate ` : duplicate an existing VM

    - Returns:

      - ` VM ` : the new duplicated VM

  - ` switch_machine ` : switch to a given machine type

    - ` machine (Machine) ` : the new machine type to switch to

    - ` interruptible (bool) ` : switches the VM to a interruptible instance. Note that this means the VM can be terminated at any point in time.

  - ` run_with_exit_code ` : run a command and get output and exit code

    - ` *commands (str) ` : the commands to run on the VM in sequence

    - Returns:

      - ` str ` : the command's output

      - ` int ` : the command's exit code

  - ` run ` : run a command and get the output. Raises an error for nonzero exit codes.

    - ` *commands (str) ` : the commands to run on the VM in sequence

    - Returns:

      - ` str ` : the command's output

  - ` upload_file ` : upload a given file to a remote path on the VM

    - ` file_path (str) ` : path to the file to upload

    - ` remote_path (Optional[str]) ` : where the path should be stored on the VM. Defaults to just the filename in the home directory.

    - ` progress_bar (bool) ` : whether to display a progress bar for this file or not. Defaults to True

  - ` download_file ` : download a file from the VM to a given target path

    - ` remote_path (str) ` : the path inside the VM to download

    - ` file_path (str) ` : the local path to store the file contents in. Defaults to the path relative to the home directory inside the VM starting from the current working directory.

  - ` download_folder ` : download a folder from the VM to a given target path

    - ` remote_path (str) ` : the path inside the VM to download

    - ` target_path (Optional[str]) ` : the local path to store the directory contents in. Defaults to the path relative to the home directory inside the VM starting from the current working directory.

  - ` install_plugin ` : install a given plugin by name

    - ` plugin_name (str) ` : the plugin to install

  - ` uninstall_plugin ` : uninstalls a given plugin by nameVM

    - ` plugin_name (str) ` : the plugin to install

  - ` run_plugin ` : runs a given plugin with the given arguments

    - ` plugin_name (str) ` : the plugin to run

    - ` *args (Any) ` : the positional arguments passed to the plugins run method

    - ` * *kwargs (Any) ` : the keyword arguments passed to the plugins run method` `


A VM object also has the following properties:

  - ` name (str) ` : the VM name

  - ` status (Status) ` : the ` Status ` of the VM. Can be one of \{ NotCreated | Pending | Running | Stopping | Stopped | Failed \}

  - ` teamspace (Teamspace) ` : the Teamspace the VM belongs to

  - ` owner (Union[User, Organization]) ` : the owner of the Teamspace the VM belongs to

  - ` machine (Optional[Machine]) ` : the machine type the VM is running on or None if it's not running

  - ` available_plugins (Mapping[str, str]) ` : a dictionary with names of available plugins as keys and their descriptions as values

  - ` installed_plugins (Mapping[str, Plugin]) ` : a dictionary with names of installed plugins as keys and the corresponding ` Plugin ` objects as values


## Teamspace[](#teamspace)

`1 2 3 4 5 6 ` ` from lightning_sdk import Teamspace teamspace = Teamspace('my-teamspace', user='my-user') all_vms = teamspace.vms print(teamspace.name)`

A Teamspace object has the following functions:

  - ` * *init ** ` : creating a Teamspace object

    - ` name (Optional[str]) ` : the name of the Teamspace

    - ` org (Optional[Union[str, Organization]]) ` : the organization owning the teamspace

    - ` user (Optional[Union[str, User]]) ` : the user owning the teamspace, Note: Since a teamspace can either be owned by an org or by a user directly, only one of the arguments can be provided.


A Teamspace object also has the following properties:

  - ` name (str) ` : the Teamspace's name

  - ` id (str) ` : the Teamspace's ID

  - ` owner (Union[User, Organization] ` \): the Teamspace's owner

  - ` studios (List[Studio]) ` : a list of all Studios in a Teamspace the authenticated user can access

  - ` vms (List[VM]) ` : a list of all VMs in a Teamspace the authenticated user can access

  - ` clusters (List[str]) ` : a list of all cluster names in that Teamspace


## Organization[](#organization)

`1 2 3 4 5 6 7 ` ` from lightning_sdk import Organization org = Organization('my-org') print(org.name) all_teamspaces = org.teamspaces`

An Organization object has the following functions:

  - ` * *init ** ` : creating an Organization object

    - ` name (Optional[str]) ` : the name of the Organization


An Organization object also has the following properties:

  - ` name (str) ` : the Organization's name

  - ` id (str) ` : the Organization's ID

  - ` teamspaces (List[Teamspace]) ` : A list of Teamspaces owned by this Organization


## User[](#user)

`1 2 3 4 5 6 ` ` from lightning_sdk import User user = User('my-user') print(user.name) all_teamspaces = user.teamspaces`

A User object has the following functions:

  - ` * *init ** ` : creating a User object

    - ` name (Optional[str]) ` : the name of the User


A User object also has the following properties:

  - ` name (str) ` : the User's name

  - ` id (str) ` : the User's ID

  - ` teamspaces (List[Teamspace]) ` : A list of Teamspaces owned by this User


## Machine & CloudProvider[](#machine-andamp-cloudprovider)

`lightning-sdk ` offers abstractions for machines and cloud providers. These can generally be used as follows:

`1 2 3 4 ` ` from lightning_sdk import Machine, CloudProvider vm = VM(name="my-new-vm", create_ok=True, cloud_provider=CloudProvider.AWS) vm.start(Machine.L4)`

Some machines \(or their variants\) are only supported on certain cloud providers. If a machine has multiple variants \(for example the A100 has 40GB and 80GB VRAM variants\), the ` Machine ` class has attributes for all of them \(e.g. ` Machine.A100_40GB ` and ` Machine.A100_80GB ` \). With multiple variants, every cloud provider usually provides only one of them \(if at all\). For better cloud agnostic machine specification, there always exists a case that's variant independent \(e.g. ` Machine.A100 ` \) that would match for all variants depending on the given cloud provider:

`1 2 3 4 5 6 7 ` ` from lightning_sdk import Machine, CloudProvider vm = VM(name="my-new-aws-vm", create_ok=True, cloud_provider=CloudProvider.AWS) vm.start(Machine.A100_X_8) # starts on Machine.A100_40GB_X_8 since AWS only provides the 40GB variant of A100s vm = VM(name="my-new-aws-vm", create_ok=True, cloud_provider=CloudProvider.GCP) vm.start(Machine.A100_X_8) # starts on Machine.A100_80GB_X_8 since GCP only provides the 80GB variant of A100s`

Some cloud providers \(mainly GCP\) provide certain instance types only for a previously determined amount of time. This amount of time can be specified in seconds with the ` max_runtime ` argumennt

`1 2 3 4 ` ` from lightning_sdk import Machine, CloudProvider vm = VM(name="my-new-aws-vm, create_ok=True, cloud_provider=CloudProvider.GCP) vm.start(Machine.H200, max_runtime=3600) # runs for 1 hour`

If not specified, the default for this argument is 3 hours where necessary and the argument will be ignored if it's set but not required.

