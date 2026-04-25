import os
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv

load_dotenv()

# Connect to Atlas
client = AsyncIOMotorClient(os.getenv("MONGO_URI"))
db = client.tenet_db
nodes_collection = db.nodes # Our DAG lives here