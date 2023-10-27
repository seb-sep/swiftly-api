from fastapi import FastAPI, Path, File, HTTPException 
from fastapi.security import HTTPBearer, OAuth2PasswordBearer
from fastapi.middleware.cors import CORSMiddleware
import os, io
from data_schema import User, Note
from pydantic import BaseModel
from typing import Annotated
import json
import openai
import queries
# only import dotenv if running locally
#from dotenv import load_dotenv
#load_dotenv()

# setup opnenai api key
openai.api_key = os.getenv("OPENAI_API_KEY")
if openai.api_key == None:
    print("No OpenAI key env var found.")
    exit()

# set up AWS region
AWS_REGION = os.getenv("AWS_REGION")
if AWS_REGION == None:
    print("No AWS region env var found.")
    exit()

token_auth_scheme = HTTPBearer()

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=['*'],
    allow_credentials=True,
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

class TitleResponse(BaseModel):
    title: str
    id: str


@app.post("/add", response_model=UserAddition)
async def add_user(user: UserAddition):
    try:
        id = await queries.add_user(user.name)
        return {"name": user.name,
                "id": str(id)}
    except queries.DuplicateKeyError:
        raise HTTPException(status_code=409, detail="Username already exists")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/{username}", response_model=UserResponse)
async def get_user(username: Annotated[str, Path(title="The username to query")]):
    user = User.objects(name=username).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
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
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    new_note = Note(title=note_title(note.content), content=note.content)
    print(new_note.content)
    user.notes.append(new_note)
    user.save()
    return note

def note_title(note: str) -> str:
    '''Generate a title for a note.'''

    completion = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": "Write a brief, unique title summarizing the following note in about five words."},
            {"role": "user", "content": note}
        ],
        max_tokens=16,
        temperature=1.5 # pick something more random to ensure uniqueness among titles
    )

    return completion.choices[0].message.content

@app.post("/transcribe")
async def transcribe(speech_bytes: Annotated[bytes, File()]):
    """Transcribe passed audio file to text."""
    contents = io.BytesIO(speech_bytes)
    contents.name = 'name.m4a'
    # with open('name.wav', 'wb') as f:
    #     f.write(contents.read())
    transcript = openai.Audio.transcribe('whisper-1', contents) 
    return transcript['text'].strip('"').strip("'")
    

@app.get("/{username}/notes")
async def get_note_titles(username: Annotated[str, Path(title="The username to query")]):
    """Fetch all note titles and IDs for a given user."""
    user = User.objects(name=username).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return [TitleResponse(title=note.title, id=str(note.id))  for note in user.notes]

@app.get("/{username}/notes/{id}")
async def get_note(
    username: Annotated[str, Path(title="The username to query")],
    id: Annotated[str, Path(title="the object id of the note to get")]
    ):
    """Fetch a note by title for a given user."""
    user = User.objects(name=username).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    note = next((note for note in user.notes if str(note.id) == id), None)
    print(note.content)
    if not note:
        raise HTTPException(status_code=404, detail="Note not found")
    return NoteAddition(
        title=note.title,
        content=str(note.content)
    )
