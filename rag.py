import os
from pymongo import MongoClient
import openai
from typing import List
import tiktoken

'''
Fuck langchain
Use text davinci 003 to check whether the top 10 cosine similarity notes are relevant or not,
then feed the ones that are into a chat completion call where the relevant notes are in the system message
https://github.com/openai/openai-cookbook/blob/main/examples/How_to_finetune_chat_models.ipynb
'''

MONGO_URI: str = os.getenv("MONGODB_URI")
if MONGO_URI == None:
    print("No MongoDB URI environment variable found.")
    exit()

openai.api_key = os.getenv("OPENAI_API_KEY")
if openai.api_key == None:
    print("No OpenAI key env var found.")
    exit()

client = MongoClient(MONGO_URI)
dbName = "langchain_demo"
collectionName = "embedding_test"
collection = client[dbName][collectionName]

def get_embedding(content: str):
    response = openai.Embedding.create(
        input=content,
        model='text-embedding-ada-002'
    )
    return response['data'][0]['embedding']

def get_relevant_notes(query: str) -> List[str]:
    embedding = get_embedding(query)

    pipeline = [
        {
            "$vectorSearch": {
                "index": "note_embeddings",
                "queryVector": embedding,
                "path": "embedding",
                "limit": 10,
                "numCandidates": 100,
            }
        },
        {
        "$project": {
            "text": 1,
        }
        }
    ]
    result = collection.aggregate(pipeline)
    return [note['text'] for note in list(result)]


def num_tokens(text: str) -> int:
    encoding = tiktoken.get_encoding('cl100k_base')
    return len(encoding.encode(text))

def chat_completion(query: str) -> str:
    notes = '\n'.join(get_relevant_notes(query))
    print(notes + '\n\n')


    response = openai.ChatCompletion.create(
        model='gpt-3.5-turbo',
        messages=[
            {'role': 'system', 'content': 'You are a personal assistant helping a person remember what their ideas and thoughts were.'},
            {'role': 'system', 'content': f'Use this newline-separated list of notes to answer all questions: {notes}'},
            {'role': 'system', 'content': 'Respond in the style of the query, and succinctly summarize the important notes to answer the question.'},
            {'role': 'user', 'content': query}
        ]
    )
    return response['choices'][0]['message']['content']




def main():
    while True:
        result = chat_completion(input("Enter query: "))
        print(result)

if __name__ == '__main__':
    main()






