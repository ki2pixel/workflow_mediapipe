# Custom inference engine[](#custom-inference-engine)

Let's learn the basics with a simple hello world server. The [next guide](https://lightning.ai/docs/litserve/home/speed-up-serving-by-200x) deploys a real server and speeds it up by 200x.


After the hello world example, you'll learn to make a blazing fast server.

Select an Image

# Hello world server[](#hello-world-server)

First install LitServe

`1 ` ` pip install litserve`

## Full server[](#full-server)

Let's deploy an AI "inference" pipeline. This pipeline has multiple "models" to illustrate the flexibility of LitServe to go beyond 1 model. As fancy as they may appear, AI models are ultimately math functions 😉.

Create a ` server.py ` file, paste this code in it and run it to deploy your model\!

Import

import the LitServe package

Define LitAPI

LitAPI describes how a server handles and responds to an incoming request

Launch Server

LitServer object starts the http server, accumulates batches, handles streaming, etc...

`1 2 3 4 5 6 7 8 9 10 11 12 13 14 15 16 17 18 19 20 21 22 23 ` ` import litserve as ls  class SimpleLitAPI(ls.LitAPI): def setup(self, device): self.model1 = lambda x: x * *2 self.model2 = lambda x: x * *3 def decode_request(self, request): return request["input"] def predict(self, x): squared = self.model1(x) cubed = self.model2(x) output = squared + cubed  return {"output": output} def encode_response(self, output): return {"output": output} if * *name ** == " * *main * *": api = SimpleLitAPI() server = ls.LitServer(api, accelerator="auto") server.run(port=8000)`

Deploy the server:

Host on Lightning

Automatically deploys secure, autoscaling endpoint to Lightning cloud.

Self host

Run anywhwere \(laptop, own server, etc...\).

`1 2 3 ` ` lightning deploy server.py --cloud  lightning deploy server.py `

## LitAPI overview[](#litapi-overview)

The first step is to implement the LitAPI class which defines the lifecycle of a * *_single request or batch_ * *.

Setup

Add 1+ models, vector DBs, caches or anything the server needs. Called once at startup.

Handle request

Map network request into something your model can consume \(images, text, etc...\).

Inference

Called with the output of decode\_request. If batched, x is a batch of inputs. Otherwise, x is a single request.

Pipeline

Run the inference pipeline \(multiple models, vector\_db, etc...\).

Format response

Called with the output of predict, structure the server response.

`1 2 3 4 5 6 7 8 9 10 11 12 13 14 15 16 17 18 19 20 21 22 23 ` ` import litserve as ls  class SimpleLitAPI(ls.LitAPI): def setup(self, device): self.model1 = lambda x: x * *2 self.model2 = lambda x: x * *3 def decode_request(self, request): return request["input"] def predict(self, x): squared = self.model1(x) cubed = self.model2(x) output = squared + cubed  return {"output": output} def encode_response(self, output): return {"output": output} if * *name ** == " * *main * *": api = SimpleLitAPI() server = ls.LitServer(api, accelerator="auto") server.run(port=8000)`

Think of this as organizing the key code from a FastAPI server into a clean, readable structure that LitServe can autoscale across workers, GPUs, etc...

## LitServer overview[](#litserver-overview)

The LitServer \(a FastAPI app\) is responsible for starting the http server, calling LitAPI at the right time, and autoscaling across GPUs, etc... All special functionality such as streaming, batching, etc... are handled by LitServer.

Run under \_\_main\_\_

LitAPI autoscales workers on a machine. Make sure to run under the \_\_main\_\_ function.

FastAPI app

LitServer is a FastAPI app under the hood

`1 2 3 4 5 6 7 8 9 10 11 12 13 14 15 16 17 18 19 20 21 22 23 ` ` import litserve as ls  class SimpleLitAPI(ls.LitAPI): def setup(self, device): self.model1 = lambda x: x * *2 self.model2 = lambda x: x * *3 def decode_request(self, request): return request["input"] def predict(self, x): squared = self.model1(x) cubed = self.model2(x) output = squared + cubed  return {"output": output} def encode_response(self, output): return {"output": output} if * *name ** == " * *main * *": api = SimpleLitAPI() server = ls.LitServer(api) server.run(port=8000)`

Enable optional features to increase performance or customize it to make specialized servers for things like LLMs or vision models.

Streaming

Enable streaming \(optional\)

Batching

Predict method will be called after accumulating 10 requests.

Specs

Write custom specs or use default one \(like OpenAI spec\).

Autoscale GPUs

Autoscales across all GPUs available on a machine

FastAPI compatible

Fully compatible with FastAPI middleware, etc...

`1 2 3 4 5 6 7 8 9 10 11 12 ` ` if * *name ** == " * *main * *": api = SimpleLitAPI( stream=True, max_batch_size=10, spec=ls.OpenAISpec() ) server = ls.LitServer( api, accelerator="auto", middlewares=[cors_middleware] ) server.run(port=8000)`

Refer to the [features section ](https://lightning.ai/docs/litserve/features) for 20+ more features.

# Hosting options[](#hosting-options)

## Lightning AI[](#lightning-ai)

Deploy servers via Lightning AI for free out-of-the-box features like scale-to-zero, autoscale up on demand, enterprise-grade RBAC, multi-node inference, and more.

https://pl-bolts-doc-images.s3.us-east-2.amazonaws.com/app-2/Deploy-Tools-GIF-1280x800.mp4

To deploy on Lightning AI, simply run LitServe with the lightning CLI. This will automatically package the server into a Docker container \(which you can configure\), upload to the Lightning container registry, and deploy to a serverless endpoint.

`1 ` ` lightning deploy server.py --cloud`

Connect your cloud on Lightning AI to deploy via your own private cloud \(VPC\). This also lets you consume your cloud credits, enterprise-commitments, etc...


Select an Image

## Self host[](#self-host)

You can also run LitServe anywhere you want and manage the hosting yourself. Simply run in local mode.

`1 ` ` lightning deploy server.py`

# Next Steps[](#next-steps)

Deploy a [realistic example](https://lightning.ai/docs/litserve/home/speed-up-serving-by-200x) [ ](https://lightning.ai/docs/litserve/home/tuning-guide) and learn to make it 200 times faster.


Next example shows how to deploy a realistic model and scale it from 11 requests per second to 1432 \(100x faster\).

Select an Image

