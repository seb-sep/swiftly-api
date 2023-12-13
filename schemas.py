from pydantic import BaseModel


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

class NoteResponse(BaseModel):
    title: str
    content: str


