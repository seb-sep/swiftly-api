from pymongo import MongoClient
from langchain.embeddings.openai import OpenAIEmbeddings
from langchain.vectorstores import MongoDBAtlasVectorSearch
from langchain.llms import OpenAI
from langchain.chains import RetrievalQA
from langchain.schema import Document
import os

MONGO_URI: str = os.getenv("MONGODB_URI")
if MONGO_URI == None:
    print("No MongoDB URI environment variable found.")
    exit()

OPENAI_APIKEY = os.getenv("OPENAI_API_KEY")
if OPENAI_APIKEY == None:
    print("No OpenAI key env var found.")
    exit()

client = MongoClient(MONGO_URI)
dbName = "langchain_demo"
collectionName = "embedding_test"
collection = client[dbName][collectionName]

embeddings = OpenAIEmbeddings(openai_api_key=OPENAI_APIKEY)

def init_embeddings():
    with open('./test_notes.txt', 'r') as f:
        test_notes = f.read()
        docs = [Document(page_content=note) for note in test_notes.split('\n\n')]


    embeddings = OpenAIEmbeddings(openai_api_key=OPENAI_APIKEY)
    vectorStore = MongoDBAtlasVectorSearch.from_documents(docs, embeddings, collection=collection)

def query_data(query):
    # Convert question to vector using OpenAI embeddings
    # Perform Atlas Vector Search using Langchain's vectorStore
    # similarity_search returns MongoDB documents most similar to the query    

    vectorStore = MongoDBAtlasVectorSearch(collection, embeddings)
    docs = vectorStore.similarity_search(query)
    # print(len(docs))
    # as_output = docs[0].page_content

    # Leveraging Atlas Vector Search paired with Langchain's QARetriever

    # Define the LLM that we want to use -- note that this is the Language Generation Model and NOT an Embedding Model
    # If it's not specified (for example like in the code below),
    # then the default OpenAI model used in LangChain is OpenAI GPT-3.5-turbo, as of August 30, 2023
    
    llm = OpenAI(openai_api_key=OPENAI_APIKEY, temperature=0)


    # Get VectorStoreRetriever: Specifically, Retriever for MongoDB VectorStore.
    # Implements _get_relevant_documents which retrieves documents relevant to a query.
    retriever = vectorStore.as_retriever()
    relevant_stuff = retriever.get_relevant_documents(query)
    print(relevant_stuff)

    # Load "stuff" documents chain. Stuff documents chain takes a list of documents,
    # inserts them all into a prompt and passes that prompt to an LLM.

    qa = RetrievalQA.from_chain_type(llm, chain_type="stuff", retriever=retriever)

    # Execute the chain

    retriever_output = qa.run(query)

    # Return Atlas Vector Search output, and output generated using RAG Architecture
    return retriever_output

def main():
    while True:
        query = input("Query: ")
        retriever_output = query_data(query)
        print("LLM Output: ", retriever_output)
main()

'''
Fuck langchain
Use text davinci 003 to check whether the top 10 cosine similarity notes are relevant or not,
then feed the ones that are into a chat completion call where the relevant notes are in the system message
https://github.com/openai/openai-cookbook/blob/main/examples/How_to_finetune_chat_models.ipynb
'''