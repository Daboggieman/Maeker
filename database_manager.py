import os
from pymongo import MongoClient # type: ignore
from dotenv import load_dotenv

load_dotenv()

class DatabaseManager:
    def __init__(self):
        self.uri = os.getenv("MONGODB_URI")
        if not self.uri:
            print("WARNING: MONGODB_URI not found in environment.")
            self.client = None
            self.db = None
        else:
            try:
                # Setting a shorter timeout 
                client = MongoClient(self.uri, serverSelectionTimeoutMS=5000, connectTimeoutMS=5000)
                client.admin.command('ping')
                self.client = client
                self.db = client['maker_studio']
                print("Connected to MongoDB Atlas.")
            except Exception as e:
                print(f"CRITICAL WARNING: MongoDB connection failed ({e}). Running in LOCAL mode.")
                self.client = None
                self.db = None

    def save_content_metadata(self, metadata):
        if self.db is not None:
            # Upsert the metadata based on the _id if it exists, otherwise insert new
            obj_id = metadata.get("_id")
            if obj_id:
                return self.db.content_metadata.replace_one({"_id": obj_id}, metadata, upsert=True)
            else:
                return self.db.content_metadata.insert_one(metadata)
        return None

    def update_job_status(self, job_id, status):
        if self.db is not None:
            return self.db.job_queue.update_one({"_id": job_id}, {"$set": {"status": status}})
        return None

if __name__ == "__main__":
    db = DatabaseManager()
