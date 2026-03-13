# AI Studio \(workspace\)[](#ai-studio-workspace)

AI Studio is a persistent, collaborative GPU cloud workspace that feels like a local laptop - with AI copilots that help you debug, train, inference, and ship like a pro.

Use the Studio to train models, run inference, code together, build agents, AI apps and more. Visit the [environments hub](https://lightning.ai/environments) to see what over 350,000 other developers and researchers have built with Lightning Studio\!

\(If you just need a VM [follow this guide](https://lightning.ai/docs/overview/vm-ssh) \).

https://pl-bolts-doc-images.s3.us-east-2.amazonaws.com/app-2/develop-1.mp4

Example of a Studio

# Quick Start[](#quick-start)

## Create a free account[](#create-a-free-account)

Click "Start free" \(or [here](https://lightning.ai/sign-up) \) to create a free account - * *no credit card required. **

Verify your phone number to receive 80 free GPU hours each month. This step is required for your security. Purchase additional GPU hours as needed. * *_New accounts start on our generous _ * * [free tier](https://lightning.ai/pricing#tiers) with features like free ssh, connect any IDE, unlimited background execution, and more \( [pricing](https://lightning.ai/pricing#tiers) \).

Tip: Use a work or university email for instant verification. Otherwise you will be put on a waitlist. We process sign up requests within 48 hours. Lightning is not available in every country.

https://pl-bolts-doc-images.s3.us-east-2.amazonaws.com/Docs\_Studios\_MP4/Overview\_CreateAccount2.mp4

Learn more about [account creation](https://lightning.ai/docs/overview/getting-started/create-account) .

## Add credits[](#add-credits)

All users receive 15 free credits each month \(1 credit equals $1 USD\). To purchase additional credits, click the balance icon and add credits. Free credits reset monthly, while purchased credits expire 12 months from the purchase date.

Tip: Please reach out for * *bulk credit discounts * *.

https://pl-bolts-doc-images.s3.us-east-2.amazonaws.com/Docs\_Studios\_MP4/TeamManagement\_Organizations\_ManageCosts\_AddCredits.mp4

## Start instance[](#start-instance)

Start a new Studio by typing [studio.lightning.ai](https://studio.lightning.ai/) on your browser or click the "New Studio" button from the dashboard.

The Studio automatically starts on a free CPU instance. The first 4-CPU instance on any cloud is always free. We recommend you install your code, dependencies, packages while on the free CPU Studio and only switch to a GPU when you're ready to run. This will save you a LOT of money.

## Connect to instance \(UI\)[](#connect-to-instance-ui)

Instances come with pre-packaged VSCode and JupyterLab, accessible directly from the browser \( [view it here](https://studio.lightning.ai/) \). We promise it is very fast and offer unique features like live collaboration and GPU metrics. Otherwise, use ssh to connect any local IDE such as VSCode, Cursor, PyCharm and more \( [full guide](https://lightning.ai/docs/overview/studios/connect-local-ide) \).

https://pl-bolts-doc-images.s3.us-east-2.amazonaws.com/Docs\_Studios\_MP4/Docs\_Studios\_ConnectLocalIDE\_ConnectSSH.mp4

## Connect to instance \(SSH\)[](#connect-to-instance-ssh)

For experts who just need a remote ssh instance, simply click ssh at the top \(read the [full guide](https://lightning.ai/docs/overview/studios/ssh-access) \).

Connecting to a remote instance via SSH allows you to maintain a local workflow with all changes happening on the remote instance ⚡️⚡️ - this is like Google Cloud for your code.

https://pl-bolts-doc-images.s3.us-east-2.amazonaws.com/Docs\_Studios\_MP4/Docs\_Studios\_SSHAccess2.mp4

# Key features[](#key-features)

Studios differ quite a bit from just renting a GPU VM, here are some key features.

## AI copilot[](#ai-copilot)

Each Studio comes prebuilt with AI copilots that we've trained to be experts on everything AI/ML... from training models, building inference engines, to debugging CUDA and expert-level PyTorch.

Choose any model or contact us to connect/deploy your own on-prem models.


Select an Image

## Native persistent storage[](#native-persistent-storage)

Studios include persistent storage, allowing file and data downloads to remain intact even if the instance stops, without incurring costs.

For existing data, use the [Lightning Drive](https://lightning.ai/docs/overview/studios/drive) \- a shared filesystem across all Studios. The Drive enables [data uploads via the browser](https://lightning.ai/docs/overview/studios/drive#upload-data) , [SDK](https://lightning.ai/docs/overview/studios/drive#upload-via-sdk) , or [connections to S3 buckets and EFS volumes.](https://lightning.ai/docs/overview/studios/drive#connect-s3-buckets) It also supports creating new S3 or EFS volumes directly \(contact us to request early access\).

Persistent storage lets you seamlessly resume work without re-downloading or prepping data again, conserving valuable GPU hours for work, not prep. Additionally, the Drive’s shared filesystem enables your team to easily share files without the need to duplicate them.

https://pl-bolts-doc-images.s3.us-east-2.amazonaws.com/Docs\_Studios\_MP4/Docs\_Studios\_Drive\_ConnectS3Bucket.mp4

## Native persistent environment[](#native-persistent-environment)

Studios automatically save the environment \(persist\). This includes installed packages \(pip, conda, etc.\), package builds, custom Python versions, downloaded files \(via git, etc.\), and more. Everything within the Studio home \( ` ~`, ` /teamspace/studios/this_studio ` \) is saved automatically.

Each Studio includes conda and supports only one conda environment. For additional environments, create new Studios. Persistent environments allow a Studio to be turned off to save costs and resumed later without loss of data or progress. We recommend to create one Studio per project or conda environment.

https://pl-bolts-doc-images.s3.us-east-2.amazonaws.com/Docs\_Studios\_MP4/Docs\_Studios\_EnvironmentPersistency\_InstallPackages.mp4

Studios persist the environment automatically

## Treat a Studio like your laptop[](#treat-a-studio-like-your-laptop)

Now that the Studio is up and running, go ahead and do anything you’d do on your laptop. Git clone repos, download files, install packages, build Docker images, and more.

If you ever wonder, "How can I do this on a Studio?" just try the same thing you would on your laptop:

Add row above

Add row below

Delete row

Add column to left

Add column to right

Delete column

Laptop

Studio

Can I git clone?

Open terminal + ` git clone`

Open terminal + ` git clone`

Can I install XYZ package?

Open terminal + ` pip install`

Open terminal + ` pip install`

Can I build a docker image?

Open terminal + ` docker ps`

Open terminal + ` docker ps`

However, the Studio unlocks new ways of working that are not possible on your laptop. Examples:

Add row above

Add row below

Delete row

Add column to left

Add column to right

Delete column

Laptop

Studio

Run code for days?

Can't close laptop

Close the Studio, code keeps running

Need a GPU?

Submit a job \(slow iteration cycle\)

Press a button and switch to a GPU

Scale to multi-node

Not possible

Press button, scale to N machines

Start from scratch

Can't throw away laptop

Delete Studio and start a new one

Code with others \(like Google Docs\)

Not possible

Press a button, share a link

Run a Streamlit app

Can't share it publicly

Can share with a button press

All installs and files are always there?

Yes

Yes

Start 100 jobs with same environment?

Not possible

Press button, scale to 100 copies of the Studio

Share a project with someone

Need git + install instructions + hours of debugging

Share a link, other person can duplicate the Studio in < 2 minutes

## Code together[](#code-together)

Studio's shared coding feature is ideal for quick collaborative tasks like peer debugging, environment setup, helping a junior peer. Remember, it doesn't replace version control. Use it for solo development and bring in others for targeted assistance or short collaborations.

Try it now\! Go ahead and i * *nvite someone to code with you. **

https://pl-bolts-doc-images.s3.us-east-2.amazonaws.com/Docs\_Studios\_MP4/Docs\_Studios\_Collaboration\_LiveCoding\_Full.mp4

Tip: This feature has cool use cases like running coding interviews on GPUs, and even helping students during classes.

## Stop instance[](#stop-instance)

When Studios are idle for more than 10 minutes, they will automatically sleep. Auto-sleep massively reduces cloud costs and minimizes wasted GPU hours.

To manually stop the instance, simply press the "turn off" button on the GPU switcher.

https://pl-bolts-doc-images.s3.us-east-2.amazonaws.com/Docs\_Studios\_MP4/Docs\_Studios\_BackgroundExecution\_AutoSleepCloud2.mp4

An example of auto sleep.

## Connect cloud account[](#connect-cloud-account)

Security-conscious teams can run Lightning Studios on private VPCs, utilizing existing cloud credits and commitments. All traffic is secure, ensuring no data leaves the VPC.

Contact us to upgrade to the [enterprise tier](https://lightning.ai/pricing#tiers) to run Lightning on your own VPC.

https://pl-bolts-doc-images.s3.us-east-2.amazonaws.com/Docs\_Studios\_MP4/Organizations\_ManageOrgClusters\_CreateCloud.mp4

## Automate with SDK[](#automate-with-sdk)

Everything we discussed here can be automated with our SDK.

`1 ` ` pip install lightning-sdk `

Here's an example pipeline that prepares data, trains a model and deploys the model. Each Studio is completely isolated from each other and self-contained. This drastically simplifies pipeline building with Studios.

`1 2 3 4 5 6 7 8 9 10 11 12 13 14 15 16 17 18 19 20 ` ` # login to the platform # export LIGHTNING_USER_ID=000000-000000-000000-00000-000000000 # export LIGHTNING_API_KEY=111111-111111-111111-11111-111111111 from lightning_sdk import Machine, Studio data_prep_studio = Studio("data_preparation") data_prep_studio.start(Machine.DATA_PREP) data_prep_studio.run("python prepare_data.py") data_prep_studio.stop() train_studio = Studio("training") train_studio.start(Machine.V100_X_4) train_studio.run("python train.py --data_path /teamspace/studios/data_preparation/preprocessed_data") train_studio.stop() deploy_studio = Studio("deploy") deploy_studio.start(Machine.T4) deploy_studio.run("python deploy_server.py --checkpoint /teamspace/studios/training/checkpoints/last.ckpt") # leave it running to serve requests`

## Start from a template or Quest[](#start-from-a-template-or-quest)

We recommend to start a Quest to get familiar with the platform

Invalid Studio URL

Invalid Studio URL

Invalid Studio URL

Or find a [template](https://lightning.ai/studios) , here are a few suggested ones:

Invalid Studio URL

Invalid Studio URL

Invalid Studio URL

Invalid Studio URL

Invalid Studio URL

Invalid Studio URL

If you have your own code and data, then simply git clone it or upload it to a [fresh Studio](https://studio.lightning.ai/) .

# Next steps[](#next-steps)

Now that you've created your first Studio, create more Studios \( [studio.lightning.ai](https://studio.lightning.ai/) \) for each project you are working on\!


Set up a Studio for each project you work on

Select an Image

Sleeping Studios don't cost anything. Set up a Studio for every project you are working on and turn it on when you need it\! If you want to run multiple Studios at a time or use GPUs, then you'll use up your free credits. When you run out, simply buy more credits.

To unlock more features, [upgrade to one of the Tiers](https://lightning.ai/pricing) or [contact our sales team](https://lightning.ai/pricing) for custom deals tailored to your company and use case.

