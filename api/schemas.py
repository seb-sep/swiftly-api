from pydantic import BaseModel
from datetime import datetime

class Note(BaseModel):
    title: str
    content: str

class NoteAddition(BaseModel):
    content: str

class UserAddition(BaseModel):
    name: str

class UserAdditionResponse(BaseModel):
    name: str
    id: str

class UserResponse(BaseModel):
    name: str
    notes: list[Note]

class NoteTitle(BaseModel):
    id: str # the id of the note
    title: str # the title of the note
    created: str
    favorite: bool

class NoteResponse(BaseModel):
    title: str
    content: str
    created: datetime
    favorite: bool

class SetFavorite(BaseModel):
    favorite: bool

