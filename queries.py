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
    try:
        global client
        client.close()
    except Exception as e:
        print(f'Error closing db connection: {e}')

async def start_db_connection():
    '''
    Start the database connection.
    '''
    global client
    client = motor_asyncio.AsyncIOMotorClient(MONGO_URI)

async def get_client() -> motor_asyncio.AsyncIOMotorClient:
    global client
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
    note_id = ObjectId()
    note = {
        'id': note_id, # generate a new id for the note
        'title': title,
        'content': content,
        'created': datetime.datetime.utcnow(),
        'favorite': False
    }
    result = await users.update_one({'name': username}, {'$push': {'notes': note}})
    if result.modified_count == 0:
        raise ValueError("User not found")
    try:
        result = await users.find_one({'name': username}, projection={'_id': 1})
        user_id = result['_id']
        await add_vector(str(user_id), note_id, content)
    except Exception as e:
        print(f'Error adding vector: {e}')

async def add_vector(user_id: str, note_id: ObjectId, content: str):
    '''
    Add a vector for the given note to the note_vectors collection.i
    '''

    client = await get_client()
    vectors = client['test']['note_vectors']
    embedding = await get_embedding(content)
    result = await vectors.insert_one({'user_id': user_id, 'note_id': note_id, 'embedding': embedding})
    return result


async def get_user_titles(username: str) -> List[NoteTitle]:
    '''
    Get the titles of all notes for the given user.

    :raises ValueError if the user does not exist
    '''

    client = await get_client()
    try:
        users = client['test']['user']
    except Exception as e:
        raise ValueError(f'Error getting user collection: {e}')

    
    pipeline = [
        { "$match": { "name": username } },
        { "$unwind": "$notes" },
        { "$sort": { "notes.created": -1 } },
        { "$project": { "_id": 0, "title": "$notes.title", "id": "$notes.id", "created": "$notes.created", "favorite": "$notes.favorite" }}
    ]


    result = await users.aggregate(pipeline).to_list(length=None)

    try:
        return [NoteTitle(title=note['title'], 
                          id=str(note['id']), 
                          created=str(note['created']), 
                          favorite=bool(note['favorite'])) for note in result]
    except Exception as e:
        print(f'Error getting user titles: {e}')

    
    
async def get_user_note(username: str, note_id: str) -> NoteResponse: 
    '''
    Get the content of the note with the given id for the given user.

    :raises ValueError if the user or note does not exist
    '''
    
    client = await get_client()
    users = client['test']['user']

    pipeline = [
        {
            "$match": {
                "name": username  
            }
        },
        {
            "$unwind": "$notes"
        },
        {
            "$replaceRoot": {
                "newRoot": "$notes"
            }
        },
        {
            "$match": {
                "id": ObjectId(note_id)
            }
        },
        {
            "$project": {
                "title": 1,
                "content": 1,
                "created": 1,
                "favorite": 1,
            }
        },
    ]

    result = await users.aggregate(pipeline).to_list(length=1)
    if result == None:
        raise ValueError("Note not found")
    note = result[0]
    return NoteResponse(title=note['title'], 
                        content=note['content'], 
                        created=str(note['created']), 
                        favorite=bool(note['favorite']))

async def del_user_note(username: str, note_id: str):
    '''
    Delete the note with the given id for the given user.

    :raises ValueError if the user or note does not exist
    '''
    
    client = await get_client()
    users = client['test']['user']

    
    result = users.update_one({'name': username}, {'$pull': {'notes': {'id': ObjectId(note_id)}}})

    if result == None:
        raise ValueError("Note not found")
    
async def set_user_note_favorite(username: str, note_id: str, favorite: bool):
    '''
    Set the favorite status of the note with the given id for the given user.

    :raises ValueError if the user or note does not exist
    '''
    
    client = await get_client()
    users = client['test']['user']

    
    result = users.update_one({'name': username, 'notes.id': ObjectId(note_id)}, {'$set': {'notes.$.favorite': favorite}})

    if result == None:
        raise ValueError("Note not found")


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
    embedding = await get_embedding(query)
    
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
