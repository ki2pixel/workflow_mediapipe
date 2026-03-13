# Interruptible machines[](#interruptible-machines)

Use interruptible machines to save 50-80% on the standard machine costs. For example, a $4.00 GPU machine can cost ~$0.50 per hour when the machine is interruptible. This gets you way more power for your buck. The "catch" is that the machine can be interrupted at any time and you may experience file loss. However, in practice interruptions are rare, and in those rare cases, file loss is also extremely rare.

_Note: Upgrade to _ [ _paid tiers_](https://lightning.ai/pricing)  _to start using interruptible machines_

## Switch to interruptible machines[](#switch-to-interruptible-machines)

Open the machine selector, turn on the "Interruptible" switch, and pick your machine. Once you’ve chosen, just hit "Confirm" to request the machine.

For [BYOC](https://lightning.ai/docs/team-management/organizations/manage-organization-clusters) , the Lightning cost stays the same. You’ll see the savings directly on your cloud bill.

_Note: Interruptible machine prices can change, but they are always cheaper than non-interruptible options._

https://pl-bolts-doc-images.s3.us-east-2.amazonaws.com/Docs\_Studios\_MP4/Overview\_Studios\_InterruptibleMachines.mp4

When selecting a machine, turn on the interruptible toggle and choose an interruptible machine. Savings can be seen for each instance.

## Handling interruptions[](#handling-interruptions)

Interruptions are rare, but they can occur. If they do, Studios and jobs immediately start saving to secure your work. You won’t be able to use them while saving. Cloud providers give Lightning a two-minute warning before shutting down the machine, Lightning uses that time to save as much data as possible.

https://pl-bolts-doc-images.s3.us-east-2.amazonaws.com/Docs\_Studios\_MP4/Overview\_Studios\_InterruptibleMachines\_HandlingInterruptions.mp4

If interruptible machines are interrupted, studios and jobs immediately start saving to secure your work.

## Minimizing disruptions[](#minimizing-disruptions)

Keep your work safe by building in these practices:

  - * *Regular checkpoints ** : Save your data and checkpoints to disk at regular intervals. It’s a simple way to cut down on lost progress if an interruption occurs.

  - * *Fault-tolerant workloads ** : Build your applications and workflows with fault tolerance in mind. Include mechanisms that let your workload pick up right where it left off if an interruption happens.


## Default to interruptible[](#default-to-interruptible)

By default, Studios start on non-interruptible machines. If you want to save some credits, you can switch this setting to use interruptible machines instead.

To save money on your org's workloads, go to your Teamspace settings > General > Studio preferences > and switch on “Start Studios on interruptible machines.”


Save money the Studios to automatically start on interruptible machines

Select an Image

# Tracking savings[](#tracking-savings)

Keep an eye on your credit savings from interruptible machines in the Activity tab of your teamspace or organization settings.

https://pl-bolts-doc-images.s3.us-east-2.amazonaws.com/Docs\_Studios\_MP4/Overview\_Studios\_InterruptibleMachines\_TrackingActivity.mp4

The activity tab within your teamspace or organization settings shows the money spent and saved using interruptible machines.

For a closer look at your spend, click an activity. You’ll see a detailed breakdown showing which machines were interruptible and how much you saved.

https://pl-bolts-doc-images.s3.us-east-2.amazonaws.com/Docs\_Studios\_MP4/Overview\_Studios\_InterruptibleMachines\_TrackingSavings.mp4

Click an Activity to see a closer look of the savings on interruptible machines.

