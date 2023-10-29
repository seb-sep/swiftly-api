from pymongo import MongoClient
from langchain.embeddings.openai import OpenAIEmbeddings
from langchain.vectorstores import MongoDBAtlasVectorSearch
from langchain.document_loaders import TextLoader
from langchain.llms import OpenAI
from langchain.chains import RetrievalQA
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
collectionName = "collection_of_text_blobs"
collection = client[dbName][collectionName]

loader = TextLoader('./test_notes.txt')
data = loader.load()

embeddings = OpenAIEmbeddings(openai_apikey=OPENAI_APIKEY)
vectorstore = MongoDBAtlasVectorSearch.from_