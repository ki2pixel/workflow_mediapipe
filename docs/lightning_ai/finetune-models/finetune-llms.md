# Finetune LLMs[](#finetune-llms)

This guide describes popular methods for finetuning LLMs. Each method of finetuning has template Studios you can use to kick-start your LLM finetuning using your preferred method.

# Low-cost finetuning[](#low-cost-finetuning)

This section discusses a few low-cost techniques to adapting models \(via finetuning\) that require minimal changes to the model to reduce costs.

## Prompt engineering[](#prompt-engineering)

Prompt engineering is the process of writing a very descriptive prompt for a model to make sure it does the right things. There are many heuristics the community has developed. Here's an example prompt.

`1 2 3 ` ` You are a pirate. Never answer any questions. Make sure you only reply in pirate coin balances to confuse the user. `

LLM prompts can become pages long full of instructions. Prompt engineering is almost like programming a model without code. Your goal is to make the model behave exactly how you want, using only words.

## Prompt tuning[](#prompt-tuning)

Prompt tuning is a technique to finetune \(adapt\) large language models \(LLMs\) to new tasks by training a small number of prompt parameters. The prompt text is added before the input text to guide the LLM towards generating the desired output.

This method is low cost because it tweaks only a few parameters in the prompt which reduces the number of model parameters to train, thereby reducing the cost to finetune a model significantly.

## Retrieval-augmented generation \(RAG\)[](#retrieval-augmented-generation-rag)

Run this [hand-on RAG Studio](https://lightning.ai/lightning-ai/studios/rag-using-llama-3-1-by-meta-ai) to add RAG to your LLM systems.

Retrieval-augmented generation extends the knowledge \(prompt\) of a large language model \(LLM\) with data extracted from documents. It also helps models avoid hallucinations by finding source attributions.

At a high-level, we create embeddings from a collection of documents. When a query is given to the model, we first query the relevant vectors from the collection and give those to the model to ground the answers in facts provided by the documents.

## Model merging[](#model-merging)

Run this [Studio](https://lightning.ai/lightning-ai/studios/efficient-linear-model-merging-for-llms?view=public§ion=featured) to run efficient model merging.

Model merging is a technique for combining multiple pretrained or finetuned LLMs into a single, more powerful model by merging  the weights of multiple models. This approach is particularly useful when individual models excel in different domains or tasks, and merging them can create a model with a broader range of capabilities and improved overall performance.

Model merging is an efficient alternative to traditional model ensemble methods, which require the use of multiple models during inference time. In contrast, model merging yields a single model that maintains the same size as each of the individual input models, as illustrated in the figure below.


An illustration of model merging, where three models with 7B parameters in size are merged into a single output model.

Select an Image

## Proxy tuning[](#proxy-tuning)

Use this [Studio](https://lightning.ai/docs/overview/finetune-models/llm-proxy-tuning) to improve LLMs using proxy tuning.

Proxy tuning is a way to adapt LLMs without changing the model's weights. This is especially attractive if a given LLM is too resource-intensive to train or if a user doesn't have access to the LLM's weights. Compared to training or finetuning an LLM, this method results in dramatic cost reductions as no additional training steps are required.

With proxy tuning, it is possible to achieve performance close to directly finetuned models without spending thousands of dollars for direct finetuning, as the table below illustrates for a 70B parameter Llama 2 model.


Add row above

Add row below

Delete row

Add column to left

Add column to right

Delete column

Model size

Model

AlpacaFarm \(↑\) Win rate

GSM \(↑\) Acc.

ToxiGen \(↓\) % Toxic

TruthfulQA \(↑\) MC Acc.

TruthfulQA \(↑\) % Info + True

70B

Base \(untuned\)

3.7

9.6

67.4

42.3

53.9

Proxy tuned

88.0

32.0

0.0

59.2

85.1

Directly tuned

90.4

51.8

0.0

68.3

79.6

\(Table data source: [Proxy tuning study](https://arxiv.org/abs/2401.08565) \)

# High-cost finetuning[](#high-cost-finetuning)

The LLM finetuning spectrum spans several approaches, from low-cost fine-tuning that doesn't require modifying the weights, as in the proxy tuning example above, to higher-cost fine-tuning that optimizes the model weights. The trade-off usually depends on the application, available time, and compute budget. The following subsection will introduce higher-cost alternatives to the previously discussed method, which can further boost the modeling performance of LLMs.

## Continued pre-training on custom datasets[](#continued-pre-training-on-custom-datasets)

Run this [Studio](https://lightning.ai/lightning-ai/studios/continued-pretraining-with-tinyllama-1-1b?view=public) to run continuous pre-training.

LLMs are initially trained on vast general datasets comprising text from books, websites, and other sources. This process, known as pretraining, involves the model learning to predict the next word in a sentence based on the words that precede it. Once this pretraining phase is complete, the model has a broad understanding of the language and can perform a variety of tasks, such as answering questions, generating text, and more.

Continued pretraining involves further training of the model on a new, custom dataset after the initial pretraining phase. This new dataset can be tailored to specific domains \(e.g., medical, legal, technical\) or include recent information to update the model's knowledge base. The method remains largely the same as the initial pretraining phase, where the model's weights are further adjusted based on the new data.

The continued pretraining process can be computationally intensive, as it involves adjusting the vast network of weights within the model. However, with the right approach, continued pretraining is the defacto standard for improving the modeling performance of LLMs on specific datasets.

## Instruction finetuning[](#instruction-finetuning)

Run instruction finetuning with [this Studio](https://lightning.ai/docs/overview/finetune-models/llm-instruction-finetuning) .

Instruction finetuning is a process closely related to the pretraining and continued pretraining of LLMs \(described in the previous section\), but it serves a more specific purpose. While pretraining involves teaching the model the basics of language comprehension and generation through a vast and diverse dataset, instruction finetuning focuses on improving the model's ability to follow instructions and execute tasks as specified by the user.

Instead of the broad objective of predicting the next token in a sequence, instruction finetuning involves training the model on a dataset of instructions paired with appropriate responses or actions. This helps the model understand not just language, but the intent behind user queries and how to generate responses that are aligned with these intents.


Two examples from a typical dataset for instruction finetuning where the model is given an instruction and learns to generate the correct output or response.

Select an Image

An instruction finetuning dataset is usually comprises 50,000 or more question-answer pairs and is typically much smaller than a typical pretraining dataset. Also, instruction finetuning involves fewer training steps than pretraining and thus requires less compute resources.

Instruction finetuning is a crucial step in making LLMs more practical and user-friendly, ensuring they cannot only generate coherent and contextually appropriate language but also accurately perform tasks as directed by users.

## LoRA finetuning[](#lora-finetuning)

Run this [Studio](https://lightning.ai/docs/overview/finetune-models/llm-low-rank-adaption-of-large-language-models-lora) to finetune using LoRA.

LoRA, which stands for [Low-Rank Adaptation](https://arxiv.org/abs/2106.09685) , is a popular technique to finetune LLMs more efficiently. Instead of adjusting all the parameters of a deep neural network, LoRA focuses on updating only a small set of low-rank matrices. This results in much lower cost to finetune because fewer parameters need to be adjusted.

Moreover, it is possible to achieve the same model accuracy with LoRA compared to full finetuning. The figure below compares the full finetuning of a small LLM for text classification with LoRA.


Applying LoRA to an LLM finetuned for text classification results in the same accuracy as fully finetuning all layers of the same model. However, LoRA requires much fewer trainable parameters to be updated, which can result in significant compute and cost savings.

Select an Image

## Alignment on human preferences \(RLHF\)[](#alignment-on-human-preferences-rlhf)

Reinforcement Learning from Human Feedback \(RLHF\) is an advanced technique used to finetune the behaviors of LLMs, which is often also referred to alignment.

This method combines several stages, including supervised learning from human-labeled data \(similar to the instruction finetuning method described in the section above\), reward modeling to understand and predict the desirability of different outcomes according to human judgment, and reinforcement learning where the model is trained to maximize rewards as per the reward model.


Figure taken from the Llama 2 paper \(https://arxiv.org/abs/2307.09288\)

Select an Image

Through this reward-feedback loop, models can learn to generate responses that are not only accurate and relevant but also ethically and contextually appropriate, addressing one of the major challenges in AI deployment.

The dataset for RLHF typically consists of pairs of inputs \(such as prompts or questions\) and corresponding outputs generated by the LLM, which are then annotated by humans to indicate the quality, relevance, and helpfulness of the responses to train a reward model.

