import os
from pymongo import MongoClient
import openai
from typing import List
import tiktoken
from queries import get_user_titles, get_user_note
from bson import ObjectId
from schemas import NoteResponse
import dotenv

''' 
Fuck langchain
Use text davinci 003 to check whether the top 10 cosine similarity notes are relevant or not,
then feed the ones that are into a chat completion call where the relevant notes are in the system message
https://github.com/openai/openai-cookbook/blob/main/examples/How_to_finetune_chat_models.ipynb
'''

print('Getting env values...')
print(dotenv.dotenv_values())

MONGO_URI: str = os.getenv("MONGODB_URI")
if MONGO_URI == None:
    print("No MongoDB URI environment variable found.")
    exit()

OPENAI_KEY = os.getenv("OPENAI_API_KEY")
openai.api_key = OPENAI_KEY
if OPENAI_KEY == None:
    print("No OpenAI key env var found.")
    exit()

client = MongoClient(MONGO_URI)
users = client['test']['user']
vectors = client['test']['note_vectors']

def get_embedding(content: str):
    response = openai.Embedding.create(
        input=content,
        model='text-embedding-ada-002'
    )
    return response['data'][0]['embedding']

def add_vector(user_id: str, note_id: ObjectId, content: str):
    embedding = get_embedding(content)
    result = vectors.insert_one({'user_id': user_id, 'note_id': note_id, 'embedding': embedding})
    
    print(result)

def insert_vectors(username: str):
    user = users.find_one({'name': username}, projection={'user._id': 1, 'notes.id': 1, 'notes.content': 1})
    for note in user['notes']:
        # Make the user id a string since you're filtering on it, but the note id an object id since you're joining on it
        add_vector(str(user['_id']), note['id'], note['content'])

async def main():
    await get_user_note('sebmichaelsep@gmail.com', '65258891fce42ffaa5bda7ea')

def get_relevant_notes(user_id: str, query: str) -> List[str]:
    embedding = get_embedding(query)
    
    pipeline = [
        {
            "$vectorSearch": {
                "path": "embedding",
                "index": "default",
                "queryVector": embedding,
                "numCandidates": 100,
                "limit": 10,
                "filter": {
                    "user_id": { "$in": [user_id] }
                }
            }
        },
        
        {
            "$project": {
                "_id": 0,
                "note_id": 1,
            }
        },
        {
            "$unwind": "$note_id"
        },
    ]
    
    ids = vectors.aggregate(pipeline)
    print(ids)

    pipeline = [
        {
            "$match": {
                "_id": ObjectId(user_id)
            }
        },
        {
            "$unwind": {
                "path": "$notes",
            }
        },
        {
            "$replaceRoot": {
                "newRoot": "$notes"
            }
        },
        {
            "$match": {
                "id": {"$in": [note['note_id'] for note in list(ids)]}
            }
        },
        {
            "$project": {
                "content": 1
            }
        },
    ]
    notes = users.aggregate(pipeline)
    return [note['content'] for note in list(notes)]


async def get_user_note(username: str, note_id: str) -> NoteResponse: 
    '''
    Get the content of the note with the given id for the given user.

    :raises ValueError if the user or note does not exist
    '''
    
    user = users.find_one({'name': username, 'notes.id': ObjectId(note_id)}, projection={'notes.title': 1, 'notes.content': 1})
    if user == None:
        raise ValueError("User not found")


def chat_completion(query: str) -> str:
    notes = '\n'.join(get_relevant_notes("65258460abd88a55974a87bb", query))
    # print(notes + '\n\n')


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

if __name__ == '__main__':
    dotenv.load_dotenv()
    env = dotenv.dotenv_values()
    print(f'Environment variables: {env}')
    for username in ["collegestuff@gmail.com", "allenlinsh@gmail.com","dhananjai284@gmail.com"]:
        insert_vectors(username)




