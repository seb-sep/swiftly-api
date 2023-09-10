from fastapi import FastAPI, Depends, Path, UploadFile, File
from fastapi.security import HTTPBearer
from fastapi.middleware.cors import CORSMiddleware
import os
from data_schema import User, Note
from mongoengine import connect
from pydantic import BaseModel
from typing import Annotated
import boto3
import json
from botocore.config import Config

# only import dotenv if running locally
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

# set up AWS region
AWS_REGION = os.getenv("AWS_REGION")
if AWS_REGION == None:
    print("No AWS region env var found.")
    exit()

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
    new_note = Note(title=str(hash(note.content)), content=note.content)
    user.notes.append(new_note)
    user.save()
    return note

@app.post("/transcribe")
async def transcribe(speech_bytes: Annotated[bytes, File()]):
    try:
        transcript = query_endpoint(speech_bytes, 'audio/wav')
        return transcript
    except Exception as e:
        return str(e)
    

def query_endpoint(body, content_type) -> str: 
    endpoint_name = 'jumpstart-dft-hf-asr-whisper-small'
    my_config = Config(region_name=AWS_REGION)
    client = boto3.client('runtime.sagemaker', config=my_config)
    response = client.invoke_endpoint(EndpointName=endpoint_name, ContentType=content_type, Body=body)
    model_predictions = json.loads(response['Body'].read())
    return model_predictions['text']


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
    print(user)
    note = next((note for note in user.notes if note.title == title), None)
    note
    return NoteAddition(
        title=note.title,
        content=note.content
    )
