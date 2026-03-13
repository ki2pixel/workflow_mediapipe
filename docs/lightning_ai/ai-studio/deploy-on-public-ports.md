# Deploy on public ports[](#deploy-on-public-ports)

Studios can expose arbitrary APIs and apps running on servers. These exposed servers also support serverless where the Studio will turn off if the app is not being used and will turn on again if it is being used.

https://pl-bolts-doc-images.s3.us-east-2.amazonaws.com/Docs\_Studios\_MP4/Studio\_HostServerAPIs.mp4

Enable auto start so that the Studio will sleep when the Server API is not being used

# Expose servers[](#expose-servers)

This section describes how to expose servers that do not have web interfaces, ie: APIs.

## Use the API builder[](#use-the-api-builder)

To expose a server via a public API, install the API builder plugin, create a new API and run your server on the Studio.

https://pl-bolts-doc-images.s3.us-east-2.amazonaws.com/Docs\_Studios\_MP4/Studio\_HostServerAPIs\_UseAPIBuilder01.mp4

Using the API buidler to create a new API.

Now access the API from any other machine with an internet connection.

https://pl-bolts-doc-images.s3.us-east-2.amazonaws.com/Docs\_Studios\_MP4/Studio\_HostServerAPIs\_UseAPIBuilder02.mp4

Accessing the API

## Add security[](#add-security)

Restrict access to your endpoint by enabling security. There are 2 ways of securing an endpoint in the API builder.

### Token authentication[](#token-authentication)

Token-based authentication is a protocol that generates encrypted security tokens. It enables users to verify their identity to websites, which then generates a unique encrypted authentication token.

https://pl-bolts-doc-images.s3.us-east-2.amazonaws.com/Docs\_Studios\_MP4/DeployAIWebApps\_StreamlitApps\_01\_TokenAuthorization.mp4

Token based authentication demo

### Basic authentication[](#basic-authentication)

Basic Authentication is a method for an HTTP user agent \(e.g., a web browser\) to provide a username and password when making a request. When employing Basic Authentication, users include an encoded string in the Authorization header of each request they make.

https://pl-bolts-doc-images.s3.us-east-2.amazonaws.com/Docs\_Studios\_MP4/DeployAIWebApps\_StreamlitApps\_02\_BasicAuthorization.mp4

Basic authentication demo

## Save money with serverless[](#save-money-with-serverless)

Serverless is the ability for Studios to sleep when inactive and auto-wake up when active. This saves you money and resources because the Studio only runs when it needs to.

https://pl-bolts-doc-images.s3.us-east-2.amazonaws.com/Docs\_Studios\_MP4/DeployAIWebApps\_StreamlitApps\_03\_Terminal.mp4

Serverless allows Studios to auto-wake up when active

## Multiple servers in one Studio[](#multiple-servers-in-one-studio)

Studios can host multiple servers at the same time. For example, you can deploy 5 different model APIs and configure serverless for each. Whenever any of the apps are used by a user, the Studio will wake up and render the page. If multiple apps are used, the Studio will route the requests accordingly. In this case, think of a Studio as a load balancer.

# Examples[](#examples)

## Model API[](#model-api)

This is a simple, hello world model server using our serving library litserve

`1 2 3 4 5 6 7 8 9 10 11 12 13 14 15 16 17 18 19 20 21 22 23 24 25 26 27 ` ` # server.py import litserve as ls # STEP 1: DEFINE YOUR MODEL API class SimpleLitAPI(ls.LitAPI): def setup(self, device): # Setup the model so it can be called in ` predict ` . self.model = lambda x: x * *2 def decode_request(self, request): # Convert the request payload to your model input. return request["input"] def predict(self, x): # Run the model on the input and return the output. return self.model(x) def encode_response(self, output): # Convert the model output to a response payload. return {"output": output} # STEP 2: START THE SERVER if * *name ** == " * *main * *": api = SimpleLitAPI() server = ls.LitServer(api, accelerator="auto") server.run(port=8000)`

Here are other more advanced examples

Invalid Studio URL

Invalid Studio URL

Invalid Studio URL

## Serve Hugging Face models[](#serve-hugging-face-models)

Use your preferred serving framework to deploy any Hugging Face model:

https://pl-bolts-doc-images.s3.us-east-2.amazonaws.com/Docs\_Studios\_MP4/Studios\_HostServerAPIs\_ServeaHuggingFaceModel.mp4

Example of serving a hugging face model on a Studio and making a prediction from outside of the studio

`1 2 3 4 5 6 7 8 9 10 11 12 13 14 15 16 17 18 19 20 21 ` ` import litserve as ls from transformers import pipeline class HuggingFaceLitAPI(ls.LitAPI): def setup(self, device): model_name = "distilbert-base-uncased-finetuned-sst-2-english" self.pipeline = pipeline("text-classification", model=model_name, device=0 if device=="gpu" else -1) def decode_request(self, request): return request["text"] def predict(self, text): return self.pipeline(text) def encode_response(self, output): return {"label": output[0]["label"], "score": output[0]["score"]} if * *name ** == " * *main * *": api = HuggingFaceLitAPI() server = ls.LitServer(api, accelerator="gpu", devices=4, workers_per_device=2) server.run(port=8000)`

Here are more examples:

## FastAPI endpoint[](#fastapi-endpoint)

Studios support any kind of server as long as it exposes a port. For example this studio shows how to run a fastAPI server that deploys an image classification model.

## Generic servers[](#generic-servers)

Any server that exposes a port can run in serverless mode on a Studio. Visit our [full collection of Studios for serving here](https://lightning.ai/studios?section=serving) .

