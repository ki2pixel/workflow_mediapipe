# Pipelines[](#pipelines)

Real AI systems require mixing jobs, multi-node training, autoscaling inference. Today, such systems are built with brittle glue code. Pipelines let you connect different workload types into a single pipeline.

Here's a hello world example that scrapes data, deploys a RAG server and a Discord server.


Select an Image

Define pipeline

The orchestrator and workflow executor \(with scheduling, versioning, etc...\)

Job 1: Scrape data

Simulating a web scraper that saves data to a folder shared by all nodes on the pipeline.

RAG server

Simulate a RAG server. This can autoscale horizontally on its own.

Discord server

Simulate a Discord server. Automatically answers messages by users with the knowledge of the RAG server. Can horizontally scale on its own.

Start pipeline

Runs the pipeline.

`1 2 3 4 5 6 7 8 9 10 11 12 13 14 15 16 17 18 19 20 21 22 23 24 25 26 27 28 29 30 31 32 33 ` ` import lightning_sdk.pipeline as pipes from lightning_sdk.machine import Machine  # pipeline definition pipeline = pipes.Pipeline(name='third-pipeline') # web scraper web_scraper = pipes.JobStep( name='web-scraper', studio=Studio('web-scraper'), command="python web_scrapper.py" ) # rag server rag_server = pipes.DeploymentStep( name='rag-server', studio=Studio('rag-server'), command="python rag_scrapper.py" ports=[8000], ) # discord bot discord_server = pipes.DeploymentStep( name='discord-server', studio=Studio('discord-server'), command="python discord_server.py" ports=[8000], ) # run pipeline pipeline.run( steps=[web_scraper, rag_server, discord_server] )`

# What are pipelines?[](#what-are-pipelines)

Lightning Pipelines let you compose AI-specific workflows from building blocks like:

  - Batch Jobs - for large-scale data prep, evaluation, or simulation

  - Multi-Machine Jobs \(MMTs\) - for distributed training and large compute

  - Deployment Jobs - to launch scalable inference endpoints


Each step runs in its own environment, on the machine type it needs - no more juggling multiple tools, configs, or compute clusters.

# Why Pipelines[](#why-pipelines)

Building real AI products means connecting many moving pieces:

  - Data prep

  - Training \(often multi-node\)

  - Fine-tuning and evaluation

  - Deployment

  - Monitoring and retraining


Traditional orchestration tools weren’t designed for this. Lightning Pipelines are.

Lightning Pipeline enables to compose different Lightning resources such as Batch Job, Multi Machine Job or Deployment Job together.

# Benefits[](#benefits)

  - ✅ * *AI-first orchestration: ** Purpose-built for workflows like multi-node training, hyperparameter sweeps, and terabyte-scale processing.

  - ✅ * *No glue code: ** Define pipelines in code with simple, composable steps. No brittle scripts. No YAML hell.

  - * *✅ Run anywhere: ** Each step can use its own container, hardware, and scale - CPU, GPU, single-node or multi-node.

  - ✅ * *Unified data access: ** Pipeline stages share a single filesystem, so no need to copy data between tools.

  - ✅ * *Modular and future-proof: ** Easily swap out one step \(e.g., LLaMA to DeepSeek\) without rebuilding everything.

  - ✅ * *CI/CD for AI: ** Automate retraining and redeployment on a schedule or new data arrival.


