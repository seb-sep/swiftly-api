import os
from motor import motor_asyncio
from schemas import NoteTitle, NoteResponse
from typing import List
import datetime
from bson.objectid import ObjectId


# set up MongoDB connection
MONGO_URI: str = os.getenv("MONGODB_URI")
if MONGO_URI == None:
    print("No MongoDB URI environment variable found.")
    exit()

client = motor_asyncio.AsyncIOMotorClient(MONGO_URI)
db = client['test']

users = db["user"]

async def add_user(username: str) -> str:
    '''
    Add a new user with the given username to MongoDB, and return the id of the new user.

    :raises DuplicateKeyError if the username already exists
    '''
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

    note = {
        '_id': ObjectId(), # generate a new id for the note
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
    user = await users.find_one({'name': username})
    if user == None:
        raise ValueError("User not found")

    return [NoteTitle(title=note['title'], id=str(note['id'])) for note in user['notes']]

async def get_user_note(username: str, note_id: str) -> NoteResponse: 
    '''
    Get the content of the note with the given id for the given user.

    :raises ValueError if the user or note does not exist
    '''
    user = await users.find_one({'name': username})
    if user == None:
        raise ValueError("User not found")

    for note in user['notes']:
        if str(note['id']) == note_id:
            return NoteResponse(title=note['title'], content=note['content'])

    raise ValueError("Note not found")