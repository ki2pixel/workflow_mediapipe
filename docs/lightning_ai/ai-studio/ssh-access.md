# SSH access[](#ssh-access)

Secure your Studio access with SSH \( [Secure Shell](https://en.wikipedia.org/wiki/Secure_Shell) \) for encrypted command execution, file transfers, and network services.


Select an Image

## SSH use cases[](#ssh-use-cases)

Here are example use cases for using SSH with Studios:

  - * *Remote Studio management ** : Log in to the studio to install software or perform maintenance, enhancing system reliability.

  - * *Automate Deployment ** : Streamline your workflow by using SSH for hands-off Studio management and command execution.

  - * *Secure file transfer ** : Using RSync or SFTP to transfer files programmatically into the Studio, ensuring data integrity.

  - * *Tunneling and Port Forwarding ** : Leverage SSH for secure network traffic tunneling and safeguarded port forwarding.

  - * *Script Automation ** : Use SSH for executing scripts on remote servers, simplifying backups, updates, and maintenance.

  - * *Development and Testing ** : Secure your development workflow with SSH access to servers, version control, and deployment processes.


# Web-based SSH access[](#web-based-ssh-access)

Use the Terminal plugin on the Studio to ssh into the Studio machine from the browser. If you want a local ssh connection from a laptop or external machine read the next section.

https://pl-bolts-doc-images.s3.us-east-2.amazonaws.com/Docs\_Studios\_MP4/Studios\_SSHAccess\_Web-basedSSHAccess.mp4

Use the Terminal plugin to ssh into the Studio machine from the browser.

# Setup local SSH access[](#setup-local-ssh-access)

Use the following instructions to connect to a Studio from a Mac, Linux or Windows machine.

https://pl-bolts-doc-images.s3.us-east-2.amazonaws.com/Docs\_Studios\_MP4/Docs\_Studios\_SSHAccess2.mp4

Connect via ssh

## Mac and linux[](#mac-and-linux)

  1. Click " * *Connect via SSH ** " in the Terminal plugin on the right toolbar. Select your OS, and copy the displayed command.

  2. On your machine, paste the command, and hit Enter. You'll see output like this:


The command will generate the following output. To connect, simply type the ssh command copy the command that starts with ` ssh ` , paste it into the same terminal window and press Enter.


Example output to connect via SSH on Mac or Linux

Select an Image

You are now connected to your Lightning Studio 🎉


Successful connection to the Lightning Studio on Mac or Linux

Select an Image

## Windows machines[](#windows-machines)

For Windows users, initiate SSH through Powershell in Administrator mode.


Successful connection to the Lightning Studio on a Windows machine

Select an Image

## Setup a new computer[](#setup-a-new-computer)

SSH setup is a one-time process per device. If connecting from another device, you'll need to follow the setup steps again.

Select "setup new computer" in the "Connect locally via SSH" modal to re-enable your connection.


Once completed, SSH will remain enabled, just click "setup new computer" and follow remaining steps

Select an Image

# Advanced[](#advanced)

The following sections will cover adding more general purpose public and private SSH keys.

## Public keys[](#public-keys)

Public keys work in two ways: access all Studios or access a single Studio.

### All Studios[](#all-studios)

To add a public key that grants access to all Studios, click the profile image on the top right, hit Global Settings in the upcoming menu, and under the Keys tab find the SSH Keys section.


Here you can add new keys and copy and delete existing public keys

Select an Image

### Single Studio[](#single-studio)

Adding a public key to a single Studio can be done by creating a file \(e.g. ` ~/.ssh/id_rsa.pub ` \) that contains the public key.
Next, add the result to the ` authorized_keys ` file by running the following command:

`1 2 3 ` ` cat .ssh/id_rsa.pub | tee -a /lightning/authorized_keys > /dev/null `

To persist these settings, add the command to the [on-start script](https://lightning.ai/docs/overview/ai-studio/on-start-actions) .

## Private keys[](#private-keys)

Access other Studios programmatically using the [SDK](https://lightning.ai/docs/overview/developers/sdk) . Additionally, add private keys to connect to other machines. Similar to public keys, private keys can be set to all Studios or a single Studio.

### All Studios[](#all-studios)

To add a private key to all Studios, add a [Secret](https://lightning.ai/docs/security/security-features/secrets) \(e.g. ` MY_SSH_KEY ` \). Next, make your ssh-agent use the secret by running:

`1 ` ` eval ` ssh-agent -s ` > /dev/null && echo $MY_SSH_KEY | ssh-add -`

In order to persist this, add this to the [on-start script](https://lightning.ai/docs/overview/ai-studio/on-start-actions) of all relevant Studios.

### Single Studio[](#single-studio)

Providing a private SSH key for a single Studio works similar to providing it for multiple Studios. Instead of creating a [Secret](https://lightning.ai/docs/security/security-features/secrets) , create a regular SSH keyfile \(e.g. ` ~/.ssh/id_rsa ` \).

Next, add it to the SSH authentication agent by running:

`1 ` ` eval ` ssh-agent -s ` > /dev/null && cat ~/.ssh/id_rsa | ssh-add -`

To persist your key add it to your [on-start script](https://lightning.ai/docs/overview/ai-studio/on-start-actions) .

# Troubleshooting[](#troubleshooting)

"Setup new computer" to reenable the connection. If this does not resolve your issue, contact us at [support@lightning.ai](mailto:support@lightning.ai) .


Set up SSH on a new device by clicking "setup new computer"

Select an Image

