import os
from motor import motor_asyncio
from schemas import NoteTitle, NoteResponse
from typing import List
import datetime
from bson.objectid import ObjectId
from inference import get_embedding, chat_completion

# set up MongoDB connection
MONGO_URI: str = os.getenv("MONGODB_URI")
if MONGO_URI == None:
    print("No MongoDB URI environment variable found.")
    exit()

client: motor_asyncio.AsyncIOMotorClient = None

async def close_db_connection():
    '''
    Close the database connection.
    '''
    client.close()

async def get_client() -> motor_asyncio.AsyncIOMotorClient:
    client = motor_asyncio.AsyncIOMotorClient(MONGO_URI)
    return client



async def add_user(username: str) -> str:
    '''
    Add a new user with the given username to MongoDB, and return the id of the new user.

    :raises DuplicateKeyError if the username already exists
    '''
    client = await get_client()
    users = client['test']['user']
    user = {
        'name': username,
        'created': datetime.datetime.utcnow(),
        'notes': []
    }

    result = await users.insert_one(user)
    return str(result.inserted_id)

async def add_user_note(username: str, title: str, content: str):
    '''
    Add a new note with the given title and content to the user's notes.

    :raises ValueError if the user does not exist
    '''

    client = await get_client()
    users = client['test']['user']
    note = {
        'id': ObjectId(), # generate a new id for the note
        'title': title,
        'content': content,
        'created': datetime.datetime.utcnow()
    }
    result = await users.update_one({'name': username}, {'$push': {'notes': note}})
    if result.modified_count == 0:
        raise ValueError("User not found")

async def get_user_titles(username: str) -> List[NoteTitle]:
    '''
    Get the titles of all notes for the given user.

    :raises ValueError if the user does not exist
    '''
    
    client = await get_client()
    try:
        users = client['test']['user']
    except Exception as e:
        raise ValueError("Error getting user collection from db client: " + str(e))
    user = await users.find_one({'name': username}, projection={'notes.title': 1, 'notes.id': 1})
    if user == None:
        raise ValueError("User not found")
    
    return [NoteTitle(title=note['title'], id=str(note['id'])) for note in user['notes']]

async def get_user_note(username: str, note_id: str) -> NoteResponse: 
    '''
    Get the content of the note with the given id for the given user.

    :raises ValueError if the user or note does not exist
    '''
    
    client = await get_client()
    users = client['test']['user']
    note = await users.find_one({'name': username, 'notes.id': ObjectId(note_id)}, projection={'notes.title': 1, 'notes.content': 1})
    if note == None:
        raise ValueError("User not found")
    return NoteResponse(title=note['title'], content=note['content'])

async def note_chat(username: str, query: str) -> str:
    '''Take a user query and return an RAG-generated response from the user's notes.'''

    client = await get_client()
    users = client['test']['user']
    user_id = await users.find_one({'name': username}, projection={'_id': 1})
    user_id = user_id['_id']
    relevant_notes = await get_relevant_notes(str(user_id), query)
    response = await chat_completion(query, relevant_notes)
    return response


async def get_relevant_notes(user_id: str, query: str) -> List[str]:
    client = await get_client()
    vectors = client['test']['note_vectors']
    users = client['test']['user']
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
    
    ids = await vectors.aggregate(pipeline).to_list(length=10)

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
                "id": {"$in": [note['note_id'] for note in ids]}
            }
        },
        {
            "$project": {
                "content": 1
            }
        },
    ]

    notes = await users.aggregate(pipeline).to_list(length=10)
    return [note['content'] for note in notes]
