# Host web apps[](#host-web-apps)

Lightning enables developers to deploy and host web apps that can be made public or shared internally.


A web app built in Gradio.

Select an Image

# Start from a template[](#start-from-a-template)

We recommend you find a template to something similar to what you want to build by visiting our [Studio templates](https://lightning.ai/lightning-ai/studios?view=public§ion=featured) .

https://pl-bolts-doc-images.s3.us-east-2.amazonaws.com/Docs\_Studios\_MP4/DeployAIWebApps\_StartfromaTemplate2.mp4

Start from a Studio template.

# Web app frameworks[](#web-app-frameworks)

## Gradio[](#gradio)

Gradio is a web framework that mixes the front-end code with the model code. It has prebuilt templates for different machine learning tasks \(object-detection, classification, etc...\). The advantage is that it is fast to develop a visual interface to share how a model performs without needing to know web development. We recommend using this for demos, but using a more traditional web framework for production use cases.

https://pl-bolts-doc-images.s3.us-east-2.amazonaws.com/Docs\_Studios\_MP4/Deploy\_Gradio\_E2E2.mp4

Use Gradio to quickly build a demo or web application for your ML model or API.

Read the [full guide for deploying Gradio apps](https://lightning.ai/docs/overview/host-web-apps/gradio-apps) .

## Streamlit[](#streamlit)

Streamlit is a web framework that mixes the front-end code with the model code. It has a similar event-loop to React.js but it is built in pure Python. Under the hood, it still generates valid React code, but it does not require the user to know web development. This is useful to build interfaces that require computational code like in AI/ML without needing a stand-alone web app.

https://pl-bolts-doc-images.s3.us-east-2.amazonaws.com/Docs\_Studios\_MP4/Deploy\_Streamlit\_E2E.mp4

Use the Streamlit plugin to create and deploy web apps for ML and Data Science.

Read the full guide for [deploying Streamlit apps](https://lightning.ai/docs/overview/host-web-apps/streamlit-apps) .

## Traditional web frameworks[](#traditional-web-frameworks)

If you know how to build web apps, need a high-performance front-end for a model targeting a production use case, we recommend you use a traditional web framework like React or Vue.js. In this case, the front-end is separated from the ML back-end which you can treat as a black box API.

On Lightning, you can use any web development framework as well. Here's an example of React.

https://pl-bolts-doc-images.s3.us-east-2.amazonaws.com/Docs\_Studios\_MP4/DeployAIWebApps\_TraditionalWebFrameworks\_ReactApps.mp4

Use the React plugin to create a high performance web app.

# Reduce costs[](#reduce-costs)

Here we describe a few options to lower the cost of hosting web apps.

## Enable auto-start[](#enable-auto-start)

Auto-start enables apps to run 24/7, but you only pay when the app is being used actively. Under the hood, Lightning monitors user traffic to your app and turns it off when no one is using it. For example, if you get one user for 5 minutes on one day of the week, you only pay for those 5 minutes \(or it could be free if you still have free credits or a free CPU Studio\).


With auto-start, Studios sleep when the demos are not in use.

Select an Image

The downside to auto-start is that the time between requesting a URL and seeing the app may be a few minutes \(this is called the "cold-start" time\). If you find that 1-2 minute delay is too slow, then consider running the app 24/7 without auto-start.

Note: Lightning is always working toward reducing cold-start time. Every few months it gets faster and faster.

## One app per Studio[](#one-app-per-studio)

Option 1 is to set up one app per CPU Studio, enable auto-start and turn them all of. You are not charged for sleeping Studios. If you believe that multiple apps will not be used at once, then it's likely that only one Studio is running at any one time. In this case, that Studio will be free. This means you can have 20 different Studios, each running an app; as long as only one runs at a time, you'll always stay under your free Studio quota. In the rare event when multiple Studios run at the same time, then you may use us some of your free credits while multiple Studios run at the same time.


Run 1 app per CPU Studio. Keep them all asleep except for the one you want to run.

Select an Image

## Host 2+ apps in one Studio[](#host-2-apps-in-one-studio)

A second option is to run all 20 apps on a single Studio. As long as all demos fit in memory and the performance is what you want, then this guarantees that only 1 Studio is running at any one time which will keep everything free.


Host multiple apps in a Studio. Be sure that they fit in memory.

Select an Image

## Studio vs Jobs[](#studio-vs-jobs)

Apps can either be hosted via Studios or via Jobs. Studios allow interactive development and are great for debugging, testing or a simple app where you don't want to worry about a "production" deployment. We recommend hosting apps on Studios for students, scientists, and developers looking for quick prototypes.

For use cases where you may need a production workflow, we recommend you submit a Job that runs the app.

https://pl-bolts-doc-images.s3.us-east-2.amazonaws.com/Docs\_Studios\_MP4/Docs\_DevelopmentWorkflow\_Step3\_Serve+a+Model\_ProductionDevelopment.mp4

# Share apps[](#share-apps)

Lightning offers a few ways of sharing apps.

The main way to share an app is to click the public link icon on the Studio plugin you're using, either Gradio, Streamlit or React.

https://pl-bolts-doc-images.s3.us-east-2.amazonaws.com/Docs\_Studios\_MP4/DeployAIWebApps\_SharePublicLInk.mp4

Use the "Public link" button to share your web app.

To share a custom front-end or a custom app exposing ports manually, simply use the ports plugin.

https://pl-bolts-doc-images.s3.us-east-2.amazonaws.com/Docs\_Studios\_MP4/Docs\_Studios\_HostWebApps\_ExposingPorts2.mp4

Use the port plugin to manually expose your app.

