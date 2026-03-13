# Connect local IDE[](#connect-local-ide)

Connect your favorite IDE like VSCode, Cursor, Windsurf, PyCharm or just plain ssh to a Studio to code from your laptop. This will feel exactly the same as coding on your laptop, except that all code, files, and changes happen on the cloud remote Studio. If you set up profiles, settings or plug-ins in your Studio on the browser, keep in mind that these will not persist to your local IDE.

## Connect VSCode[](#connect-vscode)

Hover over the * *VSCode ** plugin and click " * *Code from local VSCode * *". Follow the instructions on the page.

https://pl-bolts-doc-images.s3.us-east-2.amazonaws.com/Docs\_Studios\_MP4/Docs\_Studios\_ConnectLocalIDE\_ConnectSSH.mp4

How to connect your local VSCode

Once you’ve connected, you can develop on VSCode installed on your laptop. The code, file and data will all execute on Lightning Studio. Once you save your files locally, they’ll be synced to the Studio.


An example of your local VSCode SSHing into your Lightning Studio

Select an Image

* *Note ** : While your local VSCode is connected to the Studio, the Studio will not auto-sleep.

## Connect IntelliJ[](#connect-intellij)

To connect IntelliJ IDEs, follow the steps described below:

Click the terminal plug in, then "Connect locally via SSH" and follow directions to expose the Username and Host information.

https://pl-bolts-doc-images.s3.us-east-2.amazonaws.com/Docs\_Studios\_MP4/Docs\_Studios\_ConnectLocalIDE\_IntelliJ\_01A.mp4

Click "Connect locally via SSH" via the terminal plugin.

Open IntelliJ, click "Remote Development SSH", and paste username and host.

https://pl-bolts-doc-images.s3.us-east-2.amazonaws.com/Docs\_Studios\_MP4/Docs\_Studios\_ConnectLocalIDE\_IntelliJ\_01B.mp4

Open up IntelliJ, click "Remote Development SSH" and paste in username and host.

Specify your private key.

https://pl-bolts-doc-images.s3.us-east-2.amazonaws.com/Docs\_Studios\_MP4/Docs\_Studios\_ConnectLocalIDE\_IntelliJ\_02.mp4

Specify your private key.

Select project directory, click "Download IDE and Connect". Now your Studio is connected to your local IntelliJ IDE.

https://pl-bolts-doc-images.s3.us-east-2.amazonaws.com/Docs\_Studios\_MP4/Docs\_Studios\_ConnectLocalIDE\_IntelliJ\_03.mp4

Select your project directory and click "Download IDE and Connect".

## Connect PyCharm[](#connect-pycharm)

To connect to PyCharm, follow the steps described below:

Click the terminal plug in, then "Connect locally via SSH" and follow directions to expose the Username and Host information.

https://pl-bolts-doc-images.s3.us-east-2.amazonaws.com/Docs\_Studios\_MP4/Docs\_Studios\_ConnectLocalIDE\_PyCharm01\_ConnectSSHTerminal.mp4

Click "Connect locally via SSH" via the terminal plugin.

Open PyCharm, click "Remote Development SSH", and paste username and host.

https://pl-bolts-doc-images.s3.us-east-2.amazonaws.com/Docs\_Studios\_MP4/Docs\_Studios\_ConnectLocalIDE\_PyCharm02\_UsernameAndHost.mp4

Open up PyCharm, click "Remote Development SSH" and paste in username and host.

Specify your private key.

https://pl-bolts-doc-images.s3.us-east-2.amazonaws.com/Docs\_Studios\_MP4/Docs\_Studios\_ConnectLocalIDE\_PyCharm03\_PrivateKey.mp4

Specify your private key.

Select project directory, click "Download IDE and Connect". Now your Studio is connected to your local PyCharm.

https://pl-bolts-doc-images.s3.us-east-2.amazonaws.com/Docs\_Studios\_MP4/Docs\_Studios\_ConnectLocalIDE\_PyCharm04\_CheckConnectionAndChooseDirectory.mp4

Select your project directory and click "Download IDE and Connect".

## Connect Cursor IDE[](#connect-cursor-ide)

Cursor is a fork of VSCode and supports all extensions and features supported by VSCode. We will repeat the same steps we followed above to connect with VSCode.

https://pl-bolts-doc-images.s3.us-east-2.amazonaws.com/Docs\_Studios\_MP4/Docs\_Studios\_ConnectLocalIDE\_ConnectCursorIDE3.mp4

How to connect to cursor IDE.

To connect to Cursor

  1. Open the terminal plugin, then select "Connect locally via SSH". Follow the instructions to reveal your Username and Host

  2. Install the ` remote-ssh ` Cursor plugin

  3. Press ` Ctrl+Shift+P ` and run the command: ` Remote-SSH: Add New SSH Host`

  4. Paste the SSH command you obtained in step 1

  5. Press ` Enter ` and select your ` ~/.ssh/config ` file if prompted

  6. Press ` Ctrl+Shift+P ` and run: ` Remote-SSH: Connect to Host`

  7. Select ` ssh.lightning.ai ` from the list.

  8. When prompted to open a folder, click on ` this_studio` ``


## Connect Windsurf IDE[](#connect-windsurf-ide)

Windsurf is a fork of VSCode, so we can connect it by following similar steps to VSCode above.


https://pl-bolts-doc-images.s3.us-east-2.amazonaws.com/Docs\_Studios\_MP4/ConnectAnyIDE-WindSurf.mp4

Connecting Windsurf via SSH

To connect to Windsurf

  1. Open the terminal plugin, then select "Connect locally via SSH". Follow the instructions to reveal your Username and Host

  2. Press ` Ctrl+Shift+P ` in Windsurf and run the command: ` Remote-SSH: Connect to SSH Host`

  3. Paste the ` <user>@ssh.lightning.ai ` part of the command you obtained in step 1

  4. Press enter to start the SSH session

  5. When prompted to open a folder, click on ` this_studio`


## Connect Antigravity[](#connect-antigravity)

Before you connect to Antigravity you must obtain your ssh key. Obtain the address by hovering your mouse pointer over “SSH” on the top right corner and then clicking “Connect via SSH”.


Select an Image

Then, you can get the SSH address.


Select an Image

Now, open Antigravity on your own local machine and click the SSH connection icon in the bottom left corner and then click “Connect to SSH Host”


Select an Image

Now, type your SSH address \(excluding “ssh” command\) and then, from there on, you can use Antigravity as usual \(e.g. cloning a Git repository\). You can check the SSH status in the bottom left corner, while everything is happening on the lightning studio.


Credit Kyunghyun Cho for the Antigravity Guide

Select an Image

## Connect other IDEs[](#connect-other-ides)

To connect other IDEs, follow the instructions for "remote servers" where you'll have to copy the SSH information the Studio gives you.


How to SSH connect to remote servers.

Select an Image

