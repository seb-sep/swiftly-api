from fastapi import FastAPI, Path, File, HTTPException 
from fastapi.security import HTTPBearer, OAuth2PasswordBearer
from fastapi.middleware.cors import CORSMiddleware
import os, io
from typing import Annotated, List
import openai
import queries
from schemas import UserAddition, NoteTitle, NoteResponse, NoteAddition
import motor

# only import dotenv if running locally
# from dotenv import load_dotenv
# load_dotenv()

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

# app.add_event_handler("startup", queries.start_db_connection)
app.add_event_handler("shutdown", queries.close_db_connection)



@app.get("/")
async def root():
    return {"message": "Hello world"}


@app.post("/users/add", response_model=UserAddition)
async def add_user(user: str):
    try:
        id = await queries.add_user(user)
        return UserAddition(name=user, id=str(id))
    except ValueError as e:
        if e.args[0] == "Username already exists":
            raise HTTPException(status_code=409, detail="Username already exists")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/users/{username}/notes/save")
async def save_note(
    username: Annotated[str, Path(title="The username to query")],
    note: NoteAddition
    ):
    """Save the new note to the user's list."""

    try:
        title = generate_note_title(note.content)
        await queries.add_user_note(
            username,
            title,
            note.content
        )
    except ValueError as e:
        if e.args[0] == "User not found":
            raise HTTPException(status_code=404, detail="User not found")
        else:
            raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    
def generate_note_title(note: str) -> str:
    '''Generate a title for a note.'''

    completion = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": "Write a brief, unique title summarizing the following note in about four words."},
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
    transcript = openai.Audio.transcribe('whisper-1', contents) 
    return transcript['text'].strip('"').strip("'")
    

@app.get("/users/{username}/notes", response_model=List[NoteTitle])
async def get_note_titles(username: Annotated[str, Path(title="The username to query")]):
    """Fetch all note titles and IDs for a given user."""

    try:
        notes = await queries.get_user_titles(username)
        return notes
    except ValueError as e:
        raise HTTPException(status_code=404, detail=f"User not found: {e.args[0]}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/users/{username}/notes/{id}", response_model = NoteResponse)
async def get_note(
    username: Annotated[str, Path(title="The username to query")],
    id: Annotated[str, Path(title="the object id of the note to get")]
    ):
    """Fetch a note by title for a given user."""

    try:
        return await queries.get_user_note(username, id)
    except ValueError as e:
        if e.args[0] == "User not found":
            raise HTTPException(status_code=404, detail="User not found")
        elif e.args[0] == "Note not found":
            raise HTTPException(status_code=404, detail="Note not found")
        else:
            raise HTTPException(status_code=500, detail=str(e.args[0]))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e.args[0]))