from mongoengine import connect, disconnect
from config import MONGO_URI

# Disconnect any existing connections
disconnect()

# Establish a connection to the MongoDB database
connect(host=MONGO_URI)