# Deploy any hugging face model[](#deploy-any-hugging-face-model)

Use this Studio to deploy any hugging face model behind a private API with [LitServe](https://github.com/Lightning-AI/litserve) .


HF model example

Select an Image

✅ Serverless \(scale to zero\)

✅ Private API

✅ Your own infrastructure

✅ Multi-GPU

✅ Add your custom HF model and HF pipeline

# Background[](#background)

## LitServe[](#litserve)

[LitServe](https://github.com/Lightning-AI/litserve) is a scalable high-performance inference engine for AI models with a minimal interface:

`1 2 3 4 5 6 7 8 9 10 11 12 13 14 15 16 17 18 19 20 21 22 23 ` ` # server.py import litserve as ls # STEP 1: DEFINE YOUR MODEL API class SimpleLitAPI(ls.LitAPI): def setup(self, device): self.model = lambda x: x * *2 def decode_request(self, request): return request["input"] def predict(self, x): return self.model(x) def encode_response(self, output): return {"output": output} # STEP 2: START THE SERVER if * *name ** == " * *main * *": api = SimpleLitAPI() server = ls.LitServer(api, accelerator="auto") server.run(port=8000)`

In this Studio we use it to deploy a private API for ANY hugging face model.

## Hugging face models[](#hugging-face-models)

Any Hugging face model \(public or private\) can be deployed with LitServe simply by overriding the methods in the LitAPI class with your custom code.

# Try it yourself[](#try-it-yourself)

Click "Open in Studio" to run this yourself.

## Define model server[](#define-model-server)

This is the model we will deploy with LitServe:

`1 2 3 4 5 6 7 8 9 10 11 12 13 14 15 16 17 18 19 20 21 22 23 24 25 26 27 28 29 30 31 ` ` import litserve as ls from transformers import pipeline class HuggingFaceLitAPI(ls.LitAPI): def setup(self, device): # Load the model and tokenizer from Hugging Face Hub # For example, using the ` distilbert-base-uncased-finetuned-sst-2-english ` model for sentiment analysis # You can replace the model name with any model from the Hugging Face Hub model_name = "distilbert-base-uncased-finetuned-sst-2-english" self.pipeline = pipeline("text-classification", model=model_name, device=0 if device=="gpu" else -1) def decode_request(self, request): # Extract text from request # This assumes the request payload is of the form: {'text': 'Your input text here'} return request["text"] def predict(self, text): # Use the loaded pipeline to perform inference return self.pipeline(text) def encode_response(self, output): # Format the output from the model to send as a response # This example sends back the label and score of the prediction return {"label": output[0]["label"], "score": output[0]["score"]} if * *name ** == " * *main * *": # Create an instance of your API api = HuggingFaceLitAPI() # Start the server, specifying the port server = ls.LitServer(api, accelerator="cuda") server.run(port=8000)`

## Step 0: Start the server[](#step-0-start-the-server)

Run the server in a terminal on the Studio,

`1 ` ` python server.py`

## Step 1: Use the model API[](#step-1-use-the-model-api)

In a terminal on the Studio, verify the server is working:

`1 ` ` python client.py`

## Step 2: Expose to the internet[](#step-2-expose-to-the-internet)

Expose the server to anyone on the internet \(you can still enable authentication optionally\)

https://www.loom.com/share/5a020b5b879940d29f7209ee07c2148f

## Step 3: Enable serverless[](#step-3-enable-serverless)

Enable "auto start" on the endpoint builder which will turn off the Studio when not in use and automatically restart it when someone uses the server.

# Conclusion[](#conclusion)

This tutorial shows how to deploy ANY Hugging Face model with LitServe.

