from fastapi import FastAPI, Depends
from fastapi.security import HTTPBearer
from dotenv import load_dotenv
import os
from schema import User
from mongoengine import connect
from pydantic import BaseModel


# set up MongoDB connection
MONGO_URI: str = os.getenv("MONGO_DB_URI")
connect(MONGO_URI)

token_auth_scheme = HTTPBearer()

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

@app.get("/private/")
async def private(token: str = Depends(token_auth_scheme)):
    result = token.credentials
    return result