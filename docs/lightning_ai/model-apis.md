# Model APIs[](#model-apis)

Add AI to your apps instantly with model APIs. Send a simple web request to a model and only pay for the tokens you use. ** _Every user gets 30 million free tokens per month._ **

First, install litAI \(or use the OpenAI Python SDK if you prefer\).

`1 ` ` pip install litai`

Now add this to your code which will call the model \(make sure you get your API key [here](https://lightning.ai/models) \).

`1 2 3 ` ` from litai import LLM llm = LLM(model="openai/gpt-5", api_key="<LIGHTNING_API_KEY>") print(llm.chat("Hello, world!"))`

[View all models](https://lightning.ai/models)


Select an Image

Add row above

Add row below

Delete row

Add column to left

Add column to right

Delete column

* *Requests per minute **

* *Tokens per minute **

Enterprise

50

200000

1Teams

30

150000

Pro

20

120000

Free

15

120000

