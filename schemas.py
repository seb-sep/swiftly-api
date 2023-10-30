from pydantic import BaseModel


class Note(BaseModel):
    title: str
    content: str

class NoteAddition(BaseModel):
    user_id: str
    content: str

class UserAddition(BaseModel):
    name: str
    id: str

class UserResponse(BaseModel):
    name: str
    notes: list[Note]

class NoteTitle(BaseModel):
    title: str # the title of the note
    id: str # the id of the note

class NoteResponse(BaseModel):
    title: str
    content: str


