# Document Search and Retrieval using RAG[](#document-search-and-retrieval-using-rag)

Use this Studio to ingest documents and build a document search and retrieval application with Retrieval Augmented Generation \(RAG\).

Click * *'🚀 Open template' ** to duplicate and customize the code in this Studio and query data from your input document.

# What is Retrieval Augmented Generation \(RAG\)[](#what-is-retrieval-augmented-generation-rag)

RAG extends the capability and knowledge base of large language models \(LLMs\) by augmenting prompts with proprietary and domain-specific knowledge without the need to retrain the LLM. It ensures information stays current and reduces hallucination by attributing the source.

This Studio is a minimal reproducible pipeline to retrieve semantically similar documents based on the input query. The next step for this Studio involves connecting an LLM and engaging in a [chat with your document](https://lightning.ai/lightning-ai/studios/document-chat-assistant-using-rag) through the retrieval pipeline.

* *_The retriever pipeline in this Studio is composed of the following components:_ **

  - * *Document Loader ** : Load the document \(.txt, .pdf, .docx, .ppt\) and perform text cleaning

  - * *Text Splitter ** : Split the document texts into multiple chunks

  - * *Embedding Generation ** : Generate vector representation of text chunks

  - * *Vector database ** : Embed and store each of the chunks and store in a vector DB

  - * *Retriever and Reranking ** : Retrieve data based on query similarity


# Run pipeline on the Studio[](#run-pipeline-on-the-studio)

Click "Open template" to run this pipeline. Once the Studio starts, run the ` rag_101/retriever.py ` script.

`rag_101/retriever.py ` is an end-to-end script that takes your input document and retrieves the semantically similar documents/chunks based on the given query.

Let's try this with an example: we will use a recent research paper, [RAG VS FINE-TUNING](https://arxiv.org/abs/2401.08406) , as our document input. The authors collected agriculture data from the USA, India, and Brazil to evaluate and compare fine-tuning LLMs and RAG. We will ask, "_ * *How many pdf data were collected from the USA? ** _". The retriever pipeline will search for the most relevant paragraph based on the question. You can run the following command in the Studio terminal to check the output of this application.

`1 ` ` python rag_101/retriever.py --file example_data/2401.08406.pdf --query "How many pdf data were collected from the USA?"`


Studio preview

Select an Image

# System architecture[](#system-architecture)

Following is a high-level architecture diagram to explain how each component works and connects with each other.


Architecture Overview

Select an Image

Let's briefly go through each of the components of this architecture.

## Full pipeline[](#full-pipeline)

Here is the complete code used for this Studio. Read on to learn more about the workflow of this application.

`1 2 3 4 5 6 7 8 9 10 11 12 13 14 15 16 17 18 19 20 21 22 23 24 25 26 27 28 29 30 31 32 33 34 35 36 37 38 39 40 41 42 43 44 45 46 47 48 49 50 51 52 53 54 55 56 57 58 59 60 61 62 63 64 65 66 67 68 69 70 71 72 73 74 75 76 77 78 79 80 81 82 83 84 85 86 87 88 89 90 91 92 93 94 95 96 97 98 99 100 101 102 103 104 105 106 107 108 109 110 111 112 113 ` ` from typing import List, Optional, Union from langchain.retrievers.document_compressors import EmbeddingsFilter from langchain.text_splitter import RecursiveCharacterTextSplitter from langchain_community.document_loaders import UnstructuredFileLoader from langchain_community.embeddings import HuggingFaceBgeEmbeddings from langchain_community.vectorstores import FAISS from rich import print from sentence_transformers import CrossEncoder from unstructured.cleaners.core import clean_extra_whitespace, group_broken_paragraphs def rerank_docs(reranker_model, query, retrieved_docs): query_and_docs = [(query, r.page_content) for r in retrieved_docs] scores = reranker_model.predict(query_and_docs) return sorted(list(zip(retrieved_docs, scores)), key=lambda x: x[1], reverse=True) def load_pdf( files: Union[str, List[str]] = "example_data/2401.08406.pdf" ) -> List[UnstructuredFileLoader]: if isinstance(files, str): loader = UnstructuredFileLoader( files, post_processors=[clean_extra_whitespace, group_broken_paragraphs], ) return [loader] loaders = [ UnstructuredFileLoader( file, post_processors=[clean_extra_whitespace, group_broken_paragraphs], ) for file in files ] return loaders def split_text( loaders: List[UnstructuredFileLoader], separators=["\n\n\n", "\n\n"], chunk_size=1000, ): text_splitter = RecursiveCharacterTextSplitter( separators=separators, chunk_size=chunk_size, chunk_overlap=300, length_function=len, is_separator_regex=False, ) docs = [] for loader in loaders: docs.extend( loader.load_and_split(text_splitter=text_splitter), ) return docs def load_embedding_model( model_name: str = "BAAI/bge-large-en-v1.5", device: str = "cuda" ) -> HuggingFaceBgeEmbeddings: model_kwargs = {"device": device} encode_kwargs = { "normalize_embeddings": True } # set True to compute cosine similarity embedding_model = HuggingFaceBgeEmbeddings( model_name=model_name, model_kwargs=model_kwargs, encode_kwargs=encode_kwargs, ) return embedding_model def load_reranker_model( reranker_model_name: str = "BAAI/bge-reranker-large", device: str = "cuda" ) -> CrossEncoder: reranker_model = CrossEncoder( model_name=reranker_model_name, max_length=512, device=device ) return reranker_model def generate_embeddings(docs, embedding_model): db = FAISS.from_documents(documents=docs, embedding=embedding_model) return db def create_compression_retriever( base_retriever, reranker_model ) -> ContextualCompressionRetriever: embeddings_filter = EmbeddingsFilter( embeddings=reranker_model, similarity_threshold=0.5 ) compression_retriever = ContextualCompressionRetriever( base_compressor=embeddings_filter, base_retriever=base_retriever ) return compression_retriever def main(file: str = "example_data/2401.08406.pdf", query: Optional[str] = None): loader = load_pdf(files=file) documents = split_text( loaders=loader, ) embedding_model = load_embedding_model() reranker_model = load_reranker_model() vectorstore = generate_embeddings(documents, embedding_model=embedding_model) retriever = vectorstore.as_retriever(search_kwargs={"k": 10}) retrieved_documents = retriever.get_relevant_documents(query) return rerank_docs(reranker_model, query, retrieved_documents) `

## Document loader[](#document-loader)

The first step is to load the given document, which can be a text file, PDF, markdown, or any other format that contains textual data. We need to read and parse the texts from the given documents and retain information.

Throughout this Studio, we use [Langchain](https://python.langchain.com/docs/get_started/introduction) , a framework for developing applications powered by language models. It provides tools and components for various workflows for building a retrieval augmented generation application.

We use [unstructured.io ](https://unstructured-io.github.io/unstructured/) integration with Langchain for data loading, which provides a high-quality open-source document preprocessing tool. It can parse complex data from PDFs and supports various file formats. You can load and query multiple documents as well. \(You can install a PDF viewer extension in VSCode to view your file\).

Following is the code to load multiple PDF documents:

`1 2 3 4 5 6 7 8 9 10 11 12 13 14 15 ` ` from langchain_community.document_loaders import UnstructuredPDFLoader from unstructured.cleaners.core import clean_extra_whitespace def load_pdf( files: List[str] = ["example_data/2401.08406.pdf", "example_data/2401.00908.pdf"] ): loaders = [ UnstructuredFileLoader( file, post_processors=[clean_extra_whitespace, group_broken_paragraphs], ) for file in files ] return loaders`

## Text splitter[](#text-splitter)

After loading the document, we get a single big chunk of text. We naturally break our conversations or textual information into small paragraphs or chunks to retrieve and comprehend one thing at a time. We will do the same thing with our document. We use Langchain's ` RecursiveCharacterTextSplitter ` class that breaks a document into multiple chunks based on a specified size.

\(Note that in Langchain, every text chunk is also referred to as a document.\)

`1 2 3 4 5 6 7 8 9 10 11 12 13 14 15 16 17 18 19 20 ` ` from langchain.text_splitter import RecursiveCharacterTextSplitter def split_text( loaders: List[UnstructuredFileLoader], separators=["\n\n\n", "\n\n"], chunk_size=1000, ): text_splitter = RecursiveCharacterTextSplitter( separators=separators, chunk_size=chunk_size, chunk_overlap=300, length_function=len, is_separator_regex=False, ) docs = [] for loader in loaders: docs.extend( loader.load_and_split(text_splitter=text_splitter), ) return docs `

## Vector database[](#vector-database)

We split the single big text into multiple chunks and generate embeddings for each of the chunks. The embeddings, usually 768 to 2048 length vectors, represent the sentences in vector form where two similar sentences will be closer and vice versa. For embedding generation, we use [BAAI/bge-large-en-v1.5](https://github.com/FlagOpen/FlagEmbedding) , an open-source model with 1024 output vector size and one of the leading models on the embedding text benchmark \( [MTEB](https://huggingface.co/spaces/mteb/leaderboard) : Massive Text Embedding Benchmark\).

We store the generated embeddings in a vector database. The vector database, also known as vector store, allows us to do a similarity search based on the input query and return the top matching documents. We will use Langchain's [FAISS](https://github.com/facebookresearch/faiss) integration, an open-source library, for efficient similarity search.

`1 2 3 4 5 6 7 8 9 10 11 12 13 14 15 16 17 18 19 ` ` from langchain_community.embeddings import HuggingFaceBgeEmbeddings from langchain_community.vectorstores import FAISS def load_embedding_model( model_name: str = "BAAI/bge-large-en-v1.5", device: str = "cuda" ) -> HuggingFaceBgeEmbeddings: model_kwargs = {"device": device} encode_kwargs = {"normalize_embeddings": True} # set True to compute cosine similarity embedding_model = HuggingFaceBgeEmbeddings( model_name=model_name, model_kwargs=model_kwargs, encode_kwargs=encode_kwargs, ) return embedding_model def generate_embeddings(docs, embedding_model): db = FAISS.from_documents(documents=docs, embedding=embedding_model) return db`

## Retrieval and re-ranking[](#retrieval-and-re-ranking)

We retrieve a list of similar documents from the vector database for the given input query. Although we use similarity search, sometimes it is common to have the most relevant document for the query to be present later in the retrieved list. A solution to this problem is to use a [Cross-Encoder](https://www.sbert.net/examples/applications/retrieve_rerank/README.html) , a model trained to predict the similarity between pairs of sentences.


Retrieval and Re-ranking \(source: Sentence Transformers\)

Select an Image

We will use [BAAI/bge-reranker-large](https://huggingface.co/BAAI/bge-reranker-large) as our cross-encoder model due to its high performance on the [MTEB benchmark](https://huggingface.co/spaces/mteb/leaderboard) . The retrieved candidate documents are again re-ranked \(sorted\) using the cross-encoder model.

`1 2 3 4 5 6 7 8 9 ` ` from sentence_transformers import CrossEncoder def rerank_docs(reranker_model, query, retrieved_docs): query_and_docs = [(query, r.page_content) for r in retrieved_docs] scores = reranker_model.predict(query_and_docs) return sorted(list(zip(retrieved_docs, scores)), key=lambda x: x[1], reverse=True) retrieved_documents = retriever.get_relevant_documents(query) reranked_documents = rerank_docs(reranker_model, query, retrieved_documents)`

## Retrieval pipeline[](#retrieval-pipeline)

Finally, we combine the above components to create our retrieval pipeline. The output you get from the retrieval pipeline is just one of the chunks that we divided earlier. You must read through the output text to find what you want. To further improve the response and format conversationally, we can connect a Large Language Model \(LLM\) and augment the retrieved document as context along with the input query. This Studio limits itself to the retrieval pipeline and will contain a full LLM-powered RAG application in the upcoming Studio.

`1 2 3 4 5 6 7 8 9 10 11 12 13 14 15 16 17 18 19 20 21 22 23 24 25 26 27 28 29 30 ` ` from rag_101.retriever import ( load_pdf, split_text, load_embedding_model, load_reranker_model, generate_embeddings, rerank_docs, ) # Load documents files = ["example_data/2401.08406.pdf", "example_data/2401.00908.pdf"] # Use your document/s loaders = load_pdf(files=files) # Split documents documents = split_text(loaders=loaders, chunk_size=1000) # Generate embeddings and store to vector database embedding_model = load_embedding_model(model_name="BAAI/bge-large-en-v1.5") reranker_model = load_reranker_model(reranker_model_name="BAAI/bge-reranker-large") db = generate_embeddings(documents, embedding_model=embedding_model) retriever = db.as_retriever(search_kwargs={"k": 10}) # Query document using the retriever query = "How many pdf data were collected from the USA?" retrieved_documents = retriever.get_relevant_documents(query) reranked_documents = rerank_docs(reranker_model, query, retrieved_documents) print(reranked_documents[0][0])`

# Conclusion[](#conclusion)

This was a minimal pipeline for retrieving and filtering documents based on the given query, which can be used to augment prompts for building LLM-powered applications. Keep an eye on the next Studio that connects an LLM with the retrieval pipeline. But for now, click the ' * *Open template ** ' button to play around with this Studio and try your document.

