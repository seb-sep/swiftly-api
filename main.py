from fastapi import FastAPI
from dotenv import load_dotenv
import os
from schema import User
from mongoengine import connect
from pydantic import BaseModel


MONGO_URI: str = os.getenv("MONGO_DB_URI")
connect(MONGO_URI)

app = FastAPI()

@app.get("/")
async def root():
    return {"message": "Hello world"}

class StudentAddition(BaseModel):
    name: str

@app.post("/add/", response_model=StudentAddition)
async def add_user(user: StudentAddition):
    new_user = User(name=user.name, notes=[])
    new_user.save()
    return user
