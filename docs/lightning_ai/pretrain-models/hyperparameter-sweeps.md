# Hyperparameter sweeps[](#hyperparameter-sweeps)

In this guide we discuss how tuning hyperparameters and performing a "sweep" can help you find the best model performance for the least training time. The result is a high-performance model while saving on cloud costs.

# Background[](#background)

Hyperparameter sweeps help you find the best performing model for the least amount of compute or time spent training. Read this section if you're unfamiliar with sweeps.

## Analogy, cookie sweep[](#analogy-cookie-sweep)

Forget about ML for a second. Imagine you are baking a cookie. You have 3 things you can change about the cookie:

  - Sugar type \(white, brown, cane\)

  - Baking time \(15 minutes, 30 minutes\)

  - Cooking temperature \(360, 400 degrees\)


There are 12 possible variations of cookies you can make. One of them will be the most delicious.

Add row above

Add row below

Delete row

Add column to left

Add column to right

Delete column

* *Sugar **

* *Baking time **

* *Cooking temperature **

* *Deliciousness score **

White sugar

15

360

?

White sugar

15

400

?

White sugar

30

360

?

White sugar

30

400

?

Brown sugar

15

360

?

Brown sugar

15

400

?

Brown sugar

30

360

?

Brown sugar

30

400

?

Cane sugar

15

360

?

Cane sugar

15

400

?

Cane sugar

30

360

?

Cane sugar

30

400

?

To find out which cookie tastes the best, you need to make all variations and assign a score. This is called a * *_hyperparameter sweep_. ** Your three hyperparameters are sugar, baking time, cooking temperature.

`1 2 3 ` ` python make_cookie.py --sugar 'white' --baking_time 15 --temperature 400 python make_cookie.py --sugar 'brown' --baking_time 15 --temperature 400 ...`

You can either make all cookies sequentially \(which will take you 4.5 hours\). Or you can get 12 kitchens and cook them all in parallel, and you'll know in 30 minutes.

If a kitchen is a GPU, then you need 12 GPUs to run each experiment to see which cookie is the best. The power of Lightning is the ability to run sweeps like this on 12 different GPUs \(or 1,000 GPUs if you'd like\) to get you the best version of a model fast.

## What is a hyperparameter[](#what-is-a-hyperparameter)

Hyperparameters are settings for a model that tweak the behavior of that model. In the cookie example, sugar, baking time and temperature are hyperparameters for the cookie recipe.

Hyperparameters are usually passed to a training script via command line arguments. Examples of hyperparameters you likely already know are * *_model type_ * *,* *_context window size_ * *and * *_learning rate_ * *.

`1 2 ` ` python train.py --model llama-2 --context_size 2048 --learning_rate 0.02`

## Why find the best parameters[](#why-find-the-best-parameters)

The question then becomes, what combination of parameters produces the best performing model? The definition of "best" depends on the work you are doing. In general, "best" refers to the lowest loss. At Lightning, we tend to think of "best" as the lowest loss _for the least amount of time spent training._

If we run this training script with 12 different hyperparameter combinations, it produces different loss curves,

`1 2 3 4 ` ` python train.py --model llama-2-7B --context_size 2048 --learning_rate 0.02 python train.py --model llama-2-70B --context_size 2048 --learning_rate 0.02 python train.py --model llama-2-70B --context_size 2048 --learning_rate 0.80 ...`


Loss curves for different hyperparameters

Select an Image

On the left, the losses went low very fast, but kind of stayed high. This is likely due to a learning rate that is too high.


Select an Image

On the right, there are a few loss curves that probably will end up at a low loss, but it will take very long to get there. This means you would have spent more money than you needed to.


Select an Image

On the middle left, we see the best loss curves. The loss reaches the lowest point in the fastest time. This means you don't have to train as long which saves you money.


Select an Image

## Generative AI sweeps[](#generative-ai-sweeps)

In generative AI, a loss curve may not show that a model has converged or that it is "the best" model. From our experience, it's common to see loss curves stay flat for a long time but the generation quality still improves. This is an example of how generation quality improves over time.


Select an Image

On the left, the model has trained for a long time. On the right, the model is just starting to train.

# Run a sweep with Lightning[](#run-a-sweep-with-lightning)

Run a hyperparameter sweep in three simple steps.

## Setup Studio[](#setup-studio)

To run a sweep with Lightning, first setup a Studio and make sure the model trains on that Studio. This is important to make sure the model doesn't crash once you run it on hundreds of GPUs and waste a ton of money.

https://pl-bolts-doc-images.s3.us-east-2.amazonaws.com/Docs\_Studios\_MP4/Docs\_TrainModel\_TuneHyperparameters01\_SetupStudio.mp4

Once your model is training successfully on a Studio, make sure your main training script can be called via command line.

https://pl-bolts-doc-images.s3.us-east-2.amazonaws.com/Docs\_Studios\_MP4/Docs\_TrainModel\_TuneHyperparameters02\_CallviaCommandLine.mp4

## Submit the sweep[](#submit-the-sweep)

Now, use the SDK to run copies of the Studio in parallel \(via Jobs\) with the parameters you are interested in. Here's example code that runs the train.py file with 3 different learning rates, each time on a separate machine in parallel.

`1 2 3 4 5 6 7 8 9 10 11 12 13 14 15 16 17 ` ` from lightning_sdk import Studio, Machine # reference to the current studio studio = Studio() # use the jobs plugin studio.install_plugin('jobs') job_plugin = studio.installed_plugins['jobs'] # do a sweep over learning rates learning_rates = [1e-4, 1e-3, 1e-2] # start all jobs on an A10G GPU with names containing an index for index, lr in enumerate(learning_rates): cmd = f'python train.py --lr {lr} --max_steps 100' job_name = f'run-2-exp-{index}' job_plugin.run(cmd, machine=Machine.A10G, name=job_name) `

## Monitor the sweep[](#monitor-the-sweep)

You'll see a list of jobs in the Jobs app where you can view logs, metrics and more

https://pl-bolts-doc-images.s3.us-east-2.amazonaws.com/Docs\_Studios\_MP4/Docs\_TrainModel\_TuneHyperparameters03\_ManageArtifacts.mp4

what's nice about sweeps with Lightning is that there is no special syntax to learn. You can use regular python control-flow which allows you to trivially do things like grid search, bayesian optimization and more without special wrappers or libraries.

## Manage artifacts[](#manage-artifacts)

Find the sweep artifacts by navigating to the job folders via the terminal. All jobs across the teamspace land here.

https://pl-bolts-doc-images.s3.us-east-2.amazonaws.com/Docs\_Studios\_MP4/Docs\_TrainModel\_TuneHyperparameters04\_ManageArtifacts\_FindSweepArtifacts.mp4

Use the terminal to find the sweep artifacts

# Sweep strategies[](#sweep-strategies)

There are multiple techniques for finding the best hyperparameters. This is an open area of research, however random search has become a simple standard.

## Grid search[](#grid-search)

A grid search tries all combinations of hyperparameters at once in parallel.

`1 2 3 4 5 6 7 8 9 10 11 12 13 14 15 16 17 18 19 20 21 ` ` from lightning_sdk import Studio, Machine # reference to the current studio studio = Studio() # use the jobs plugin studio.install_plugin('jobs') job_plugin = studio.installed_plugins['jobs'] # do a sweep over learning rates and batch sizes learning_rates = [1e-4, 1e-3, 1e-2] batch_sizes = [32, 64, 128] # a grid search combines all params grid_search_params = [(lr, bs) for lr in learning_rates for bs in batch_sizes] # start all jobs on an A10G GPU with names containing an index for index, (lr, bs) in enumerate(grid_search_params): cmd = f'python train.py --lr {lr} --batch_size {bs} --max_steps {100}' job_name = f'run-2-exp-{index}' job_plugin.run(cmd, machine=Machine.A10G, name=job_name) `

It's called a grid search because the parameter combinations generate a discrete grid


Plot of all combinations of hyperparameters

Select an Image

## Random search[](#random-search)

A grid search may generate too many combinations. [Bergstra et al](https://www.jmlr.org/papers/volume13/bergstra12a/bergstra12a.pdf) showed that one can get close to the optimal set of hyperparameters by sampling a subset of all the potential grid search combinations.

`1 2 3 4 5 6 7 8 9 10 11 12 13 14 15 16 17 18 19 20 21 22 23 24 25 ` ` from lightning_sdk import Studio, Machine from random import sample # reference to the current studio studio = Studio() # use the jobs plugin studio.install_plugin('jobs') job_plugin = studio.installed_plugins['jobs'] # do a sweep over learning rates learning_rates = [1e-4, 1e-3, 1e-2] batch_sizes = [32, 64, 128] # create a grid search first (all combinations) search_params = [(lr, bs) for lr in learning_rates for bs in batch_sizes] # perform random search with a limit of 4 combinations random_search_params = sample(search_params, 4) # start all jobs on an A10G GPU with names containing an index for index, (lr, bs) in enumerate(random_search_params): cmd = f'python train.py --lr {lr} --batch_size {bs} --max_steps {100}' job_name = f'run-1-exp-{index}' job_plugin.run(cmd, machine=Machine.A10G, name=job_name) `


Illustration of random vs grid search

Select an Image

