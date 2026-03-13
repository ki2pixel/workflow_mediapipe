# Expose web apps[](#expose-web-apps)


Select an Image

Studios can run and expose AI web apps. These public apps also support serverless where the Studio will turn off if the app is not being used and will turn on again if it is being used.

https://pl-bolts-doc-images.s3.us-east-2.amazonaws.com/Docs\_Studios\_MP4/Studios\_HostWebApps-E2E.mp4

Run and expose AI web apps via public URL.

This is a high-level guide that covers the key points of serving web apps on Studios.

For a more thorough guide check out the [deploy AI web apps section](https://lightning.ai/docs/overview/deploy-ai-web-apps) .

## Use the API builder[](#use-the-api-builder)

To expose a web app via a public URL, open a Studio and install the API builder plugin. Create a new API and add the command that will run your server. Now access the URL from a browser.

https://pl-bolts-doc-images.s3.us-east-2.amazonaws.com/Docs\_Studios\_MP4/Studios\_HostWebApps\_UsetheAPIBuilder\_CreateNewAPI.mp4

Install the API plugin to host a web app and expose a public URL.

## Save money with serverless[](#save-money-with-serverless)

Serverless is the ability for Studios to sleep when inactive and auto-wake up when active. This saves you money and resources because the Studio only runs when it needs to. For a web app, the Studio will sleep when no users are using the web app. When a user requests the web app, there will be a small delay while the app wakes up, but after that it will be instantaneous.

https://pl-bolts-doc-images.s3.us-east-2.amazonaws.com/Docs\_Studios\_MP4/Studios\_HostWebApps\_UsetheAPIBuilder\_Autostart.mp4

Save money by enabling Auto start. The studio will stay sleeping until someone visits the public URL.

## Multiple apps in one Studio[](#multiple-apps-in-one-studio)

Studios can host multiple apps at the same time. For example, you can deploy 5 different Streamlit apps and configure serverless for each. Whenever any of the apps are used by a user, the Studio will wake up and render the page. If multiple apps are used, the Studio will route the requests accordingly. In this case, think of a Studio as a load balancer.

## Exposing ports[](#exposing-ports)

Install the 'Port viewer' plug-in from the menu and open a port that exposes the UI of your application.

https://pl-bolts-doc-images.s3.us-east-2.amazonaws.com/Docs\_Studios\_MP4/Docs\_Studios\_HostWebApps\_ExposingPorts2.mp4

View the UI of your application using the 'Port viewer' plug-in.

# Examples[](#examples)

The following are various examples for common web frameworks.

## Serverless Streamlit[](#serverless-streamlit)

Streamlit is a web framework that mixes the front-end code with the model code. It has a similar event-loop to React but it is built in pure Python. Under the hood, it still generates valid React code, but it does not require the user to know web development. This is useful to build interfaces that require computational code like in AI/ML without needing a stand-alone web app.

This walk-through shows how to run a Streamlit app on a Studio with serverless enabled.

https://pl-bolts-doc-images.s3.us-east-2.amazonaws.com/Docs\_Studios\_MP4/Deploy\_Streamlit\_E2E.mp4

Runing a Streamlit app on a Studio with serverless enabled

Read this [in-depth guide](https://lightning.ai/docs/overview/deploy-ai-web-apps/streamlit-apps) on deploying Streamlit apps.

## Serverless Gradio[](#serverless-gradio)

Gradio is a web framework that mixes the front-end code with the model code. It has prebuilt templates for different machine learning tasks \(object-detection, classification, etc...\). The advantage is that it is fast to develop a visual interface to share how a model performs without needing to know web development. We recommend using this for demos, but using a more traditional web framework for production use cases.

This walk-through shows how to run a Gradio app on a Studio with serverless enabled.

https://pl-bolts-doc-images.s3.us-east-2.amazonaws.com/Docs\_Studios\_MP4/Deploy\_Gradio\_E2E2.mp4

Runing a Gradio app on a Studio with serverless enabled

Read this [in-depth guide](https://lightning.ai/docs/overview/deploy-ai-web-apps/gradio-apps) on deploying Gradio apps.

## Serverless React[](#serverless-react)

If you know how to build web apps, need a high-performance front-end for a model targeting a production use case, we recommend you use a traditional web framework like React or Vue.js. In this case, the front-end is separated from the ML back-end which you can treat as a black box API.

On Lightning, you can use any web development framework as well. Here's an example of React running serverless.

https://pl-bolts-doc-images.s3.us-east-2.amazonaws.com/Docs\_Studios\_MP4/DeployAIWebApps\_TraditionalWebFrameworks\_ReactApps.mp4

Use the React plugin to create a high performance web app.

Read this [in-depth guide](https://lightning.ai/docs/overview/deploy-ai-web-apps/reactjs) on deploying React apps.

