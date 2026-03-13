# Background execution[](#background-execution)

Studios continue to execute code even when the browser window is closed. This is called _ * *background execution * *_.

To test how this works, run code on the Studio and close the browser. Notice that the Studio is still running. Now, open the Studio on the browser and find the terminal that is executing the script.

https://pl-bolts-doc-images.s3.us-east-2.amazonaws.com/Docs\_Studios\_MP4/Docs\_Studios\_BackgroundExecution-2.mp4

A script running in a Studio

## Why use background execution[](#why-use-background-execution)

Say you want to finetune a model over many days or leave a server running or leave a data scraper running. On a laptop, you would have to keep your laptop on 24/7. With a Studio, simply start running the code and close the browser. When the code is done executing, the Studio will automatically shut down.

Note: Notebooks require the browser tab to remain open but can run in the background. This is due to a limitation with Jupyter Notebooks.

https://pl-bolts-doc-images.s3.us-east-2.amazonaws.com/Docs\_Studios\_MP4/Docs\_Studios\_BackgroundExecution\_WhyUseBackgroundExecution2.mp4

Scripts continue to run even after the browser is closed. When execution is complete, Studios auto sleep.

## Auto sleep[](#auto-sleep)

When a Studio goes to sleep, it automatically saves all details of the environments e.g packages, files, and more. When you restart the Studio, it will be ready to go as you left it.

https://pl-bolts-doc-images.s3.us-east-2.amazonaws.com/Docs\_Studios\_MP4/Docs\_Studios\_BackgroundExecution\_AutoSleepCloud2.mp4

An example of auto sleep

## Configure auto sleep[](#configure-auto-sleep)

Studios automatically sleep after * *10 minutes of inactivity. ** You can change the timeout by clicking in the environments settings. Disabling or extending auto-sleep to >10 minutes of inactivity require a Lightning Pro subscription.

https://pl-bolts-doc-images.s3.us-east-2.amazonaws.com/Docs\_Studios\_MP4/Docs\_Studios\_BackgroundExecution\_AutoSleepConfigure2.mp4

How to adjust your auto sleep settings

