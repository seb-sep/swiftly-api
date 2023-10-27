import os
import motor


# set up MongoDB connection
MONGO_URI: str = os.getenv("MONGODB_URI")
if MONGO_URI == None:
    print("No MongoDB URI environment variable found.")
    exit()

client = motor.motor_asyncio.AsyncIOMotorClient(MONGO_URI)
db = client.get_default_database()

users = db["users"]

async def add_user(username: str) -> str:
    '''
    Add a new user with the given username to MongoDB, and return the id of the new user.

    raieses DuplicateKeyError if the username already exists
    '''
    user = {
        'name': username,
        '$currentDate': {'createdAt': '$timestamp'},
        'notes': []
    }

    result = await users.insert_one(user)
    return result.inserted_id

