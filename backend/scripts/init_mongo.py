"""Create the MongoDB collections, validator and indexes for CrisisLink.

Idempotent and non-destructive: it never drops or modifies existing documents.

Run from the backend folder (PowerShell):
    python scripts/init_mongo.py
"""
import os
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_DIR))

from dotenv import load_dotenv                       # noqa: E402
load_dotenv(BACKEND_DIR.parent / '.env')

from config.mongodb import (                         # noqa: E402
    get_mongo_db, init_mongo_collections, mongo_is_available, updates_collection_name,
)

if not mongo_is_available():
    sys.exit('MongoDB is not reachable. Check that the MongoDB service is running and MONGO_URI in .env is correct.')

init_mongo_collections()
db = get_mongo_db()
col = db[updates_collection_name()]
print(f"Database   : {db.name}")
print(f"Collection : {col.name}  ({col.count_documents({})} documents)")
print("Indexes    :", ', '.join(sorted(col.index_information())))
