# Auto sleep[](#auto-sleep)

Save money on cloud costs and reduce wasted GPU spend with auto sleep. When Studios are idle for more than 10 minutes, they will automatically sleep.

https://pl-bolts-doc-images.s3.us-east-2.amazonaws.com/Docs\_Studios\_MP4/Docs\_Studios\_BackgroundExecution\_AutoSleepCloud2.mp4

An example of auto sleep.

# What is auto sleep[](#what-is-auto-sleep)

Idle Studios automatically save their state and turn off.

## What counts as idle[](#what-counts-as-idle)

If the Studio is running anything such as model training, hosting an API server, etc, it will not go to sleep.

https://pl-bolts-doc-images.s3.us-east-2.amazonaws.com/Docs\_Studios\_MP4/Docs\_Studios\_BackgroundExecution-2.mp4

A Studio continuing to run a training job.

## Environment persists[](#environment-persists)

Before a Studio sleeps, it saves your progress. This means any files you've added, packages installed, data downloaded, etc... All of these will be exactly as you left them the next time the Studio starts again.

Pro tier users can disable auto sleep, ensuring that a Studio never turns off for critical workloads. If you're using a free Studio, it will convert to a paid Studio when you disable auto-sleep.


Your Studio environment—files, packages, data, etc.—persists when a Studio sleeps and starts again.

Select an Image

## Data persists[](#data-persists)

No matter how much data you download into the Studio, it will be there next time you turn it back on\!


No matter how much data lives in a Studio, it persists between sleep and wake cycles.

Select an Image

## Cost for sleeping Studio[](#cost-for-sleeping-studio)

There is no cost for sleeping Studios, other than the storage costs for the files on that Studio.

# Modify auto-sleep settings[](#modify-auto-sleep-settings)

## Change idle timeout[](#change-idle-timeout)

A Studio auto-sleeps by default after 10 minutes of inactivity. To change this timeout setting, simply click on the machine selection button at the top right of the Studio and enter the time you prefer.


Change the auto-sleep timeout value here

Select an Image

## Remember last machine used[](#remember-last-machine-used)

Studios always restart on a CPU machine. This might feel strange to you if you come from other products where you always stay on a GPU. However, those products don't have the persistency that Studios have. On a Studio, you can develop or debug on a CPU and switch to a GPU _only _when necessary.

To remember the last used machine head to your Teamspace settings > General > Keep the same machine type when the Studio restarts.

https://pl-bolts-doc-images.s3.us-east-2.amazonaws.com/Docs\_Studios\_MP4/Docs\_Studios\_Autosleep\_RememberLastMachineUsed.mp4

Studios always restart on a CPU machine, which saves money.


Since Studios support persistent environments, they restart using a CPU.

Select an Image

Use this as an opportunity to adopt our smarter approach and move away from the habit of always coding on GPUs.

# Advantages[](#advantages)

## Save costs[](#save-costs)

Auto sleep reduces cost because Studios that aren't being used don't stay running. In addition, you are able to spend less time on GPUs and develop/debug more on CPUs and only move to GPUs when you absolutely need to.


Auto sleep prevents cost overruns by putting unused or idling Studios to sleep automatically.

Select an Image

## Reduce waste[](#reduce-waste)

Before adopting Lightning, users tend to spend more time on GPUs, since there’s not a straightforward way to switch back to a CPU. This sends compute costs soaring, although it’s preferred to setting up an environment from scratch.


Using a typical \(non-Studio\) environment, you have to rebuild your environment to switch to a CPU or incur high costs to continue using GPUs.

Select an Image

## Close the browser[](#close-the-browser)

Start your programs, close the browser and go do something else\! The Studio will automatically turn off once your program has finished executing. To check on it, simply open your Studio to see progress.

https://pl-bolts-doc-images.s3.us-east-2.amazonaws.com/Docs\_Studios\_MP4/Docs\_Studios\_BackgroundExecution\_WhyUseBackgroundExecution2.mp4

Scripts continue to run even after the browser is closed. When execution is complete, Studios auto sleep.

