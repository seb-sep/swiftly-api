from fastapi import FastAPI, Depends, Path, UploadFile, File
from fastapi.security import HTTPBearer
from fastapi.middleware.cors import CORSMiddleware
import os
from schema import User, Note
from mongoengine import connect
from pydantic import BaseModel
from typing import Annotated
import openai

# only import dotenv if running locally
from sys import platform
if platform == 'darwin':
    from dotenv import load_dotenv
    load_dotenv()


# set up MongoDB connection
MONGO_URI: str = os.getenv("MONGODB_URI")
if MONGO_URI == None:
    print("No MongoDB URI environment variable found.")
    exit()
connect(host=MONGO_URI)

# setup opnenai api key

OPENAI_APIKEY = os.getenv("OPENAI_API_KEY")
if OPENAI_APIKEY == None:
    print("No OpenAI key env var found.")
    exit()
openai.api_key = OPENAI_APIKEY

token_auth_scheme = HTTPBearer()

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=['*'],
    allow_methods=['*'],
    allow_headers=['*'],
)

@app.get("/")
async def root():
    return {"message": "Hello world"}

class NoteAddition(BaseModel):
    title: str
    content: str

class UserAddition(BaseModel):
    name: str

class UserResponse(BaseModel):
    name: str
    notes: list[NoteAddition]

User.objects

@app.post("/add/", response_model=UserAddition)
async def add_user(user: UserAddition):
    new_user = User(name=user.name, notes=[])
    new_user.save()
    return user

@app.get("/{username}", response_model=UserResponse)
async def get_user(username: Annotated[str, Path(title="The username to query")]):
    user = User.objects(name=username).first()
    return UserResponse(
        name=user.name,
        notes=list(map(lambda note: NoteAddition(
            title=note.title,
            content=note.content
        ), user.notes))
    )

@app.post("/{username}/notes/save", response_model=NoteAddition)
async def save_note(
    username: Annotated[str, Path(title="The username to query")],
    note: NoteAddition
    ):
    """Save the new note to the user's list."""
    user = User.objects(name=username).first()
    new_note = Note(title=note.title, content=note.content)
    user.notes.append(new_note)
    user.save()
    return note




@app.get("/{username}/notes")
async def get_note_titles(username: Annotated[str, Path(title="The username to query")]):
    """Fetch all note titles for a given user."""
    print(username)
    user = User.objects(name=username).first()
    return [note.title for note in user.notes]

@app.get("/{username}/notes/{title}")
async def get_note(
    username: Annotated[str, Path(title="The username to query")],
    title: Annotated[str, Path(title="The title of the note to get")]
    ):
    user = User.objects(name=username).first()
    note = next((note for note in user.notes if note.title == title), None)
    return NoteAddition(
        title=note.title,
        content=note.content
    )

@app.post("/transcribe")
async def transcribe(file: UploadFile):
    print("uploading file lololol")
    return whisper_transcribe(file.file)
    


def whisper_transcribe(file):
    try:
        transcript = openai.Audio.transcribe("whisper-1", file)
        print(transcript)
        return transcript
    except Exception as e:
        print(e)
        return e 


@app.get("/private/")
async def private(token: str = Depends(token_auth_scheme)):
    result = token.credentials
    return result
