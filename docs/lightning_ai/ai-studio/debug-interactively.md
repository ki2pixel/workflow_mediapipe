# Debug interactively[](#debug-interactively)

In this guide you'll learn to debug interactively on a Studio.

A Studio is like your laptop on the cloud. If you know how to debug on your laptop, you know how to debug on a Studio. Go ahead and use the debugger, add breakpoints, print lines, and more.

## Iteration is king[](#iteration-is-king)

A key to getting a model trained quickly is to iterate on setting up the model and getting everything to work well. Traditional workflows require you set something up locally, then submit to a remote server, wait for it to crash, and iterate to make changes. This means, that even a small code change can take 20 to 30 minutes to validate.

With Lightning, this is not a problem because you can debug interactively while testing the model on the same GPUs, data, and environment.

## Debugger[](#debugger)

The first and simplest thing is to drop a breakpoint in the VSCode debugger, run the code, and see where it stops. Here's a full walk-through of how to debug interactively using the VSCode debugger:

https://pl-bolts-doc-images.s3.us-east-2.amazonaws.com/Docs\_Studios\_MP4/Docs\_DevelopmentWorkflow\_Debugging\_VSCode.mp4

Debug via VSCode

## Via the terminal[](#via-the-terminal)

For certain uses, it's helpful to debug by running the code via a terminal. In this case, consider using pdb to programmatically add breakpoints:

https://pl-bolts-doc-images.s3.us-east-2.amazonaws.com/Docs\_Studios\_MP4/Docs\_DevelopmentWorkflow\_Debugging\_Terminal\_pdb.mp4

Debug via terminal

## Multi-GPU debugging[](#multi-gpu-debugging)

If you are running a multi-GPU program, the VSCode debugger will attach itself automatically to all processes that are created from your main program. When you set a breakpoint in a region of a program that runs in parallel, all processes will stop at this point. When you step through the code or inspect variables, this will by default be from the main process \(GPU 0\). In the "Call Stack" panel on the bottom left, you can select a different process and step/inspect it individually when it is selected. The video below shows you an example of stepping through a simple demo training loop that's using Lightning Fabric, but it works with any multi-GPU program as long as you can run it from a Python file:

https://pl-bolts-doc-images.s3.us-east-2.amazonaws.com/Docs\_Studios\_MP4/Docs\_DevelopmentWorkflow\_DebuggingInteractively\_Multi-GPU-Debugging.mp4

Debug Multi-GPU via VSCode Debugger

## From your local IDE[](#from-your-local-ide)

If you have connected your local IDE, follow the same steps we've described above for using the debugger or from a terminal or multi-GPU debugger. Here's a video showing how to debug from your local IDE:

https://pl-bolts-doc-images.s3.us-east-2.amazonaws.com/Docs\_Studios\_MP4/Docs\_DevelopmentWorkflow\_Debugging\_Local.mp4

Debug from your local IDE

## SSH into job machines[](#ssh-into-job-machines)

When you run a job from a Studio \(a job forks the environment, code, and everything else\), you have the ability to ssh into the machine that is running that job. In that machine, you can monitor system metrics manually \(the Jobs app gives you those\), or you can bind to a running python process to see what is happening.

https://pl-bolts-doc-images.s3.us-east-2.amazonaws.com/Docs\_Studios\_MP4/Docs\_DevelopmentWorkflow\_Debugging\_Jobs.mp4

SSH into job machines

