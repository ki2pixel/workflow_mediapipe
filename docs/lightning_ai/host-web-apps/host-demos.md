# Host demos[](#host-demos)

Lightning AI allows hosting AI demos for people to play with your model. An AI demo is a very simple web app often built with Gradio or Streamlit which allows a user to see the outputs of a model.


A demo built with Streamlit.

Select an Image

# Start from a template[](#start-from-a-template)

We recommend you find a template to something similar to what you want to build by visiting our [Studio templates](https://lightning.ai/lightning-ai/studios?view=public§ion=featured) ,

https://pl-bolts-doc-images.s3.us-east-2.amazonaws.com/Docs\_Studios\_MP4/DeployAIWebApps\_StartfromaTemplate2.mp4

Use the Studio template to jumpstart your App creation.

# Host demos free[](#host-demos-free)

Demos can be * *hosted for free ** by using your free running Studio and free credits. In this section, we explain a few ways to achieve that.

## Free CPU model demos[](#free-cpu-model-demos)

If your demo is CPU only, then use your free running CPU Studio which will cost you nothing. Enable auto-start which turns off the Studio when the demo is not being used.

https://pl-bolts-doc-images.s3.us-east-2.amazonaws.com/Docs\_Studios\_MP4/Serve\_Model\_HostModels\_FreeCPUModelDemos.mp4

Use your free running CPU Studio if your demo is CPU only.

## Free GPU model demos[](#free-gpu-model-demos)

GPU demos can also be free as long as the usage for the month stays under 15 credits \(~35 interruptible T4 hours\) across all your Studios.


Keep usage under 15 credits and GPU demos will remain free.

Select an Image

# Model demo frameworks[](#model-demo-frameworks)

There are multiple frameworks available to build AI demos. These frameworks intermingle the front-end with the model code in full-stack Python. The alternative is to build a stand-alone web app and a stand-alone ML micro service which is desirable for production use cases.

## Gradio demo[](#gradio-demo)

Gradio is a web frameworks that mixes the front-end code with the model code. It has prebuilt templates for different machine learning tasks \(object-detection, classification, etc...\). The advantage is that it is fast to develop a visual interface to share how a model performs without needing to know web development. We recommend using this for demos, but using a more traditional web framework for production use cases.

https://pl-bolts-doc-images.s3.us-east-2.amazonaws.com/Docs\_Studios\_MP4/Deploy\_Gradio\_E2E2.mp4

Use Gradio to quickly build a demo or web application for your ML model or API.

## Streamlit demo[](#streamlit-demo)

Streamlit is a web framework that mixes the front-end code with the model code. It has a similar event-loop to React but it is built in pure Python. Under the hood, it still generates valid React code, but it does not require the user to know web development. This is useful to build interfaces that require computational code like in AI/ML without needing a stand-alone web app.

https://pl-bolts-doc-images.s3.us-east-2.amazonaws.com/Docs\_Studios\_MP4/Deploy\_Streamlit\_E2E.mp4

Use the Streamlit plugin to create and deploy web apps for ML and Data Science.

## Traditional web frameworks[](#traditional-web-frameworks)

If you know how to build web apps, need a high-performance front-end for a model targeting a production use case, we recommend you use a traditional web framework like React or Vue.js. In this case, the front-end is separated from the ML back-end which you can treat as a black box API.

On Lightning, you can use any web development framework as well. Here's an example of React

https://pl-bolts-doc-images.s3.us-east-2.amazonaws.com/Docs\_Studios\_MP4/DeployAIWebApps\_TraditionalWebFrameworks\_ReactApps.mp4

Use the React plugin to create a high performance web app.

# Reduce costs[](#reduce-costs)

Here we describe a few options to lower the cost of hosting demos.

## One demo per Studio[](#one-demo-per-studio)

Option 1 is to set up one demo per CPU Studio, enable auto-start and turn them all of. You are not charged for sleeping Studios. If you believe that multiple demos will not be used at once, then it's likely that only one Studio is running at any one time. In this case, that Studio will be free. This means you can have 20 different Studios, each running a demo; as long as only one runs at a time, you'll always stay under your free Studio quota. In the rare event when multiple Studios run at the same time, then you may use us some of your free credits while multiple Studios run at the same time.


Keep costs minimal by running a demo on a free CPU Studio.

Select an Image

## Host 2+ demos in one Studio[](#host-2-demos-in-one-studio)

A second option is to run all 20 demos on a single Studio. As long as all demos fit in memory and the performance is what you want, then this guarantees that only 1 Studio is running at any one time which will keep everything free.


Host 20 demos in one Studio. Make sure they all fit in memory.

Select an Image

## Enable auto-start[](#enable-auto-start)

Auto-start is the main way to reduce costs by running the Studio only when someone visits the demo URL.

For example, let's say you are hosting a demo on a Studio. The Studio must run 24/7 to make sure when a user wants to use the demo, the demo is available. With auto-start enabled, the Studio automatically go to sleep when no one is using the demos. When someone visits the demo URL, the Studio will automatically wake up and show the demo. If you get one user for 5 minutes on one day of the week, you only pay for those 5 minutes \(or it could be free if you still have free credits or a free CPU Studio\).


With auto-start, Studios sleep when the demos are not in use.

Select an Image

The downside to auto-start is that the time between requesting a URL and seeing the demo may be a few minutes \(this is called the "cold-start" time\). If you find that 1-2 minute delay is too slow, then consider running the demo 24/7 without auto-start.

Note: Lightning is always working toward reducing cold-start time. Every few months it gets faster and faster.

## Studio vs Jobs[](#studio-vs-jobs)

Demos can either be hosted via Studios or via Jobs. Studios allow interactive development and are great for debugging, testing or a simple demo where you don't want to worry about a "production" deployment. We recommend hosting demos on Studios for students, scientists, and developers looking for quick prototypes.

For use cases where you may need a production workflow, we recommend you submit a Job that runs the demo. This is likely overkill for a demo however. If you're looking for a more "production-ready" way to deploy models, you likely want to use the API builder plugin to deploy a model API.

# Share demos[](#share-demos)

The main reason for building a demo is to allow anyone to play with a model to understand how it works. Lightning offers a few ways of sharing demos.

The main way to share a demo is to click the public link icon on the Studio plugin you're using, either Gradio, Streamlit or React.

https://pl-bolts-doc-images.s3.us-east-2.amazonaws.com/Docs\_Studios\_MP4/DeployAIWebApps\_SharePublicLInk.mp4

Use the "Public link" button to share your web app.

To share a custom front-end or a custom demo exposing ports manually, simply use the ports plugin.

https://pl-bolts-doc-images.s3.us-east-2.amazonaws.com/Docs\_Studios\_MP4/Deploy\_Gradio\_Port.mp4

Use the port plugin to manually expose your app.

