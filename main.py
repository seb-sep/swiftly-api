from fastapi import FastAPI, Path, File, HTTPException 
from contextlib import asynccontextmanager
from fastapi.security import HTTPBearer, OAuth2PasswordBearer
from fastapi.middleware.cors import CORSMiddleware
import os, io
from typing import Annotated, List
import queries
from schemas import UserAddition, UserAdditionResponse, NoteTitle, NoteResponse, NoteAddition, SetFavorite
from inference import generate_note_title, transcribe_audio


token_auth_scheme = HTTPBearer()

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

@asynccontextmanager
async def lifespan(app: FastAPI):
    # connect to database
    await queries.start_db_connection()
    yield
    # close database connection
    await queries.close_db_connection()

app = FastAPI(lifespan=lifespan)

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


@app.post("/users/add", response_model=UserAdditionResponse)
async def add_user(user: UserAddition):
    try:
        id = await queries.add_user(user.name)
        return UserAdditionResponse(name=user.name, id=str(id))
    except ValueError as e:
        if len(e.args) > 0 and e.args[0] == "Username already exists":
            raise HTTPException(status_code=409, detail="Username already exists")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e.args[0]) + "some random excetion")


@app.post("/users/{username}/notes/save")
async def save_note(
    username: Annotated[str, Path(title="The username to query")],
    note: NoteAddition
    ):
    """Save the new note to the user's list."""

    try:
        title = await generate_note_title(note.content)
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

    
# @app.post("/transcribe")
# async def transcribe(speech_bytes: Annotated[bytes, File()]):
#     """Transcribe passed audio file to text."""
#     contents = io.BytesIO(speech_bytes)
#     contents.name = 'name.m4a'
#     try:
#         transcript = await transcribe_audio(contents)
#         return {"text": transcript}
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=str(e))

@app.post("/users/{username}/notes/transcribe")
async def transcribe_and_save(
    username: Annotated[str, Path()],
    speech_bytes: Annotated[bytes, File()]):
    """Transcribe passed audio file to text and save it to the user's notes."""

    contents = io.BytesIO(speech_bytes)
    contents.name = 'name.m4a'
    try:
        transcript = await transcribe_audio(contents)
        title = await generate_note_title(transcript)
        await queries.add_user_note(
            username,
            title,
            transcript
        )
        return {"text": transcript}
    except ValueError as e:
        if e.args[0] == "User not found":
            raise HTTPException(status_code=404, detail="User not found")
        else:
            raise HTTPException(status_code=500, detail=str(e))

@app.post("/users/{username}/notes/chat")
async def chat_with_notes(
    username: Annotated[str, Path(title="The username to query")],
    speech_bytes: Annotated[bytes, File()]):
    """Chat with the user's notes."""

    contents = io.BytesIO(speech_bytes)
    contents.name = 'name.m4a'
    transcript = await transcribe_audio(contents)
    result = await queries.note_chat(username, transcript)
    return { "text": result }


    

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
        print(e)
        if e.args[0] == "User not found":
            raise HTTPException(status_code=404, detail="User not found")
        elif e.args[0] == "Note not found":
            raise HTTPException(status_code=404, detail="Note not found")
        else:
            raise HTTPException(status_code=500, detail=str(e.args[0]))
    except Exception as e:
        print(e)
        raise HTTPException(status_code=500, detail=str(e.args[0]))

@app.delete("/users/{username}/notes/{id}")
async def get_note(
    username: Annotated[str, Path(title="The username to query")],
    id: Annotated[str, Path(title="the object id of the note to get")]
    ):
    """Delete a given user's note."""

    try:
        await queries.del_user_note(username, id)
        return {"success": True}
    except ValueError as e:
        print(e)
        if e.args[0] == "User not found":
            raise HTTPException(status_code=404, detail="User not found")
        elif e.args[0] == "Note not found":
            raise HTTPException(status_code=404, detail="Note not found")
        else:
            raise HTTPException(status_code=500, detail=str(e.args[0]))
    except Exception as e:
        print(e)
        raise HTTPException(status_code=500, detail=str(e.args[0]))

@app.patch("/users/{username}/notes/{id}/favorite")
async def set_note_favorite(
    username: Annotated[str, Path(title="The username to query")],
    id: Annotated[str, Path(title="the object id of the note to get")],
    favorite: SetFavorite
    ):
    """Set a given user's note favorite status to the passed status."""

    try:
        await queries.set_user_note_favorite(username, id, favorite.favorite)
        return {"success": True}
    except ValueError as e:
        print(e)
        if e.args[0] == "User not found":
            raise HTTPException(status_code=404, detail="User not found")
        elif e.args[0] == "Note not found":
            raise HTTPException(status_code=404, detail="Note not found")
        else:
            raise HTTPException(status_code=500, detail=str(e.args[0]))