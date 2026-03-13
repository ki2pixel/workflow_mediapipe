# Instruction finetuning - TinyLlama 1.1B LLM[](#instruction-finetuning-tinyllama-11b-llm)

This Studio lets you finetune [TinyLlama 1.1B](https://arxiv.org/pdf/2401.02385.pdf) on a single GPU in under 10 minutes and for less than 5 credits. Included in this Studio:

  - [TinyLlama 1.1B](https://github.com/jzhang38/TinyLlama) base model checkpoint

  - Dataset \( [Alpaca2k](https://huggingface.co/datasets/mhenrichsen/alpaca_2k_test) \)

  - Finetuning recipe

  - Jupyter notebook for evaluation


# Run Studio[](#run-studio)

Click the "Open template" button above to get started.

The code is open-source and everything in it is hackable. You can take it as a starting point and change the data, the fine-tuning hyperparameters, or the base model.

# What is instruction finetuning?[](#what-is-instruction-finetuning)

During the initial phase of training, the "pretraining", a language model \(LLM\) learns from a huge and diverse dataset of natural text data with a simple task: predicting the next word. By learning to accurately predict the next word in a sequence of text, the LLM is challenged to understand the underlying patterns and structures of language and gains the ability to generate human-like text. In the [Pretrain LLMs - TinyLlama 1.1B](https://lightning.ai/lightning-ai/studios/pretrain-llms-tinyllama-1-1b?view=public§ion=featured) Studio we did exactly that.

However, this next-token prediction training does not immediately make the model useful as a chat assistant. When you give it an instruction as input, it will generate something like this:

`1 2 3 4 5 ` ` ''' >> Prompt: What do llamas eat? >> Reply: What do llamas smell like? How do you get along with llamas? Are llamas good pets? These are questions you might have if you ... ''' `

As you can see, it is just continuing the sentence as if it is one long text in a book or article. With instruction finetuning, we can further train the model to follow instructions and give meaningful responses. This is the goal of this Studio.

Note that TinyLlama was pretrained on a mix of general texts from the internet and including a large portion of source code from GitHub, so it has the potential to become a helpful coding assistant. But keep in mind that TinyLlama with its mere 1 billion parameters is tiny \(hence the name\) and won't be as capable as the [very large 70B models](https://lightning.ai/lightning-ai/studios/run-codellama-70b-instruct?view=public§ion=featured) out there.

# Finetune TinyLlama[](#finetune-tinyllama)

This section describes the recipe to finetune TinyLlama.

## Open template[](#open-template)

To finetune TinyLlama, you will need at least one GPU with 16 GB of memory. When you click "Run" on the top, the Studio will automatically start on a machine with an A10G GPU.

## About the dataset[](#about-the-dataset)

The dataset we use here is the [Alpaca2k](https://huggingface.co/datasets/mhenrichsen/alpaca_2k_test) dataset, which is a higher-quality subset of the larger [Alpaca](https://crfm.stanford.edu/2023/03/13/alpaca.html) dataset.

## Run finetuning script[](#run-finetuning-script)

You can run the finetuning in two ways, through the ` fintune.ipynb ` Jupyter notebook, or through the terminal:

`1 ` ` litgpt finetune lora --config configs/tiny-llama/lora.yaml `

And you should see the progress in the terminal output. It takes roughly 10 minutes to complete the training on the 2k examples:

`1 2 3 4 5 6 7 8 9 10 11 12 13 14 15 ` ` ... Epoch 3 | iter 715 step 715 | loss train: 0.923, val: 1.039 | iter time: 626.38 ms (step) Epoch 3 | iter 716 step 716 | loss train: 0.700, val: 1.039 | iter time: 600.36 ms (step) Epoch 3 | iter 717 step 717 | loss train: 0.688, val: 1.039 | iter time: 605.52 ms (step) Epoch 3 | iter 718 step 718 | loss train: 0.883, val: 1.039 | iter time: 683.82 ms (step) Epoch 3 | iter 719 step 719 | loss train: 0.818, val: 1.039 | iter time: 617.57 ms (step) Epoch 3 | iter 720 step 720 | loss train: 0.841, val: 1.039 | iter time: 708.08 ms (step) Epoch 3 | iter 721 step 721 | loss train: 0.847, val: 1.039 | iter time: 706.92 ms (step) Epoch 3 | iter 722 step 722 | loss train: 1.012, val: 1.039 | iter time: 707.27 ms (step) Epoch 3 | iter 723 step 723 | loss train: 0.853, val: 1.039 | iter time: 130.74 ms (step) Epoch 4 | iter 724 step 724 | loss train: 0.772, val: 1.039 | iter time: 876.49 ms (step) Training time: 485.47s Memory used: 13.50 GB Saving LoRA weights to 'out/finetune/lora-tiny-llama-1.1b/final/lit_model.pth.lora' LoRA weights have already been merged in this checkpoint. `

By default, it will use the pre-downloaded TinyLlama base model in the checkpoints folder. If you want to load a different base model, you can download it to the checkpoints folder and pass the path to via ` litgpt finetune lora --checkpoint_dir=... ` .

## Monitor training[](#monitor-training)

After you start the training, the TensorBoard log files and intermediate checkpoints will be saved to the "out/" folder in the Studio. You can easily start a TensorBoard server to inspect the log curves by selecting the TensorBoard app in the app panel located on the right-hand side of the Studio interface.


Display TensorBoard logs directly in the Studio while the finetuning is running

Select an Image

On a regular interval \(100 training steps by default\), the training will pause and run validation. At the same time, it will log a few example prompts and their outputs to the terminal and the TensorBoard logger \(see "Text" tab\). At the beginning of training, the quality of the outputs will be quite poor, but you can see them get better as training continues.

Note: The finetuning on just a single GPU is made possible thanks to a technique called [LoRA: Low-Rank Adaptation of Large Language Models](https://arxiv.org/abs/2106.09685) . If you are interested in learning how this works in detail, check out the [Code LoRA From Scratch](https://lightning.ai/lightning-ai/studios/code-lora-from-scratch?view=public§ion=featured) Studio by Sebastian Raschka.

To chat with the model, simply pass the checkpoint directory to the ` litgpt chat ` command:

`1 ` ` litgpt chat --checkpoint_dir out/finetune/lora-tiny-llama-1.1b/final`

Here are a few example prompts and responses:

`1 2 3 4 5 6 7 8 9 10 11 12 13 14 15 16 17 18 ` ` >> Prompt: How big is our solar system? >> Reply: Our solar system is a collection of eight planets, including the Sun, that orbits around our galaxy. The solar system is estimated to be between 4.6 and 4.85 billion years old, and is comprised of approximately 100 billion stars, according to NASA. This is beyond our comprehension and is one of the most intriguing and interesting mysteries of our universe. >> Prompt: Give me a math riddle (without the solution). >> Reply: What are the two numbers 5 and 8 in binary form? >> Prompt: Write an introduction to quantum computing >> Reply: Quantum computers are a type of computer that utilizes quantum mechanics to perform calculations and algorithms. They are based on the principles of quantum mechanics and use atomic nuclei to represent information, which can be either "0" or "1." This information is represented as quantum entanglement, where two quantum bits (qubits) are connected by a superposition state. This allows for the coding of information in a way that even without a classical computer, it can perform calculations much faster and more efficiently than classical computers. Quantum computing has numerous potential applications, including in science and technology, finance, and healthcare. The most prominent example is the use of quantum annealing, which is a form of optimization that uses quantum states to search for solutions to problems. However, broad applications for quantum computing are still in the early stages of development. One important advantage of quantum computers is their ability to solve problems that are currently unsolvable or infeasgnable by classical computers. For example, quantum computers can solve quadratic equations, which is a problem that classical computers are currently unable to solve.`

Try it yourself\!

## Evaluate the finetuned model[](#evaluate-the-finetuned-model)

After finetuning completes, the final checkpoint is saved to the "out/" folder. We can now evaluate the model on a set of standardized tasks \(called commonsense reasoning\) using the [EleutherAI eval harness](https://github.com/EleutherAI/lm-evaluation-harness) . Just open the ` evaluate.ipynb ` notebook in the Studio and run the cells. The evaluation will take approximately 20 minutes to run through all tasks and print a summary table with the average accuracies \(%\) with which the model completed the tasks. You can then compare these numbers to other similar models:

Add row above

Add row below

Delete row

Add column to left

Add column to right

Delete column

Model

HellaSwag

Obqa

WinoGrande

ARC\_c

ARC\_e

boolq

piqa

avg

Pythia 1.0B

47.16

31.40

53.43

27.05

48.99

57.83

69.21

48.30

Pythia 1.4B

52.01

33.20

57.38

28.50

54.00

* *63.27 **

70.95

51.33

TinyLlama 1.1B \(this Studio\)

* *58.67 **

* *36.20 **

* *60.46 **

* *29.86 **

* *54.50 **

60.95

* *73.07 **

* *53.39 **

The numbers for Pythia in the table above were taken from the [TinyLlama paper](https://arxiv.org/abs/2401.02385) . We see that TinyLlama is overall performing better than the Pythia model on these selected tasks. Note that in the case of TinyLlama here, the improvement over Pythia comes mainly from the pretraining itself.

# Conclusion[](#conclusion)

In this Studio, we learned how to instruction-finetune TinyLlama, making it respond reasonably well to questions and instructions. By leveraging LoRA, we were able to complete the finetuning on just a single GPU in less than 10 minutes. One flaw that the model still has is that it can produce harmful responses if prompted in a particular way. This is because the training data already included such texts \(from the internet\) that weren't filtered out. [Direct Preference Optimization \(DPO\)](https://arxiv.org/abs/2305.18290) is a technique that can reduce the chance that the model will output such content. In a future Studio \(coming soon\), we will explore this method in detail and use the model we finetuned here as the basis for DPO.

