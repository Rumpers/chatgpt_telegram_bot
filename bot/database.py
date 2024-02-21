from typing import Optional, Any
import pymongo
import uuid
from datetime import datetime, timedelta
import config

class Database:
    def __init__(self):
        self.client = pymongo.MongoClient(config.mongodb_uri)
        self.db = self.client["chatgpt_telegram_bot"]

        self.user_collection = self.db["user"]
        self.dialog_collection = self.db["dialog"]
        self.journal_collection = self.db["journal_entries"]

    def check_if_user_exists(self, user_id: int, raise_exception: bool = False):
        if self.user_collection.count_documents({"_id": user_id}) > 0:
            return True
        else:
            if raise_exception:
                raise ValueError(f"User {user_id} does not exist")
            return False

    def add_new_user(self, user_id: int, chat_id: int, username: str = "", first_name: str = "", last_name: str = ""):
        if not self.check_if_user_exists(user_id):
            self.user_collection.insert_one({
                "_id": user_id,
                "chat_id": chat_id,
                "username": username,
                "first_name": first_name,
                "last_name": last_name,
                "last_interaction": datetime.now(),
                "first_seen": datetime.now(),
                "current_dialog_id": None,
                "current_chat_mode": "assistant",
                "current_model": config.models["available_text_models"][0],
                "n_used_tokens": {},
                "n_generated_images": 0,
                "n_transcribed_seconds": 0.0
            })

    def start_new_dialog(self, user_id: int):
        self.check_if_user_exists(user_id, raise_exception=True)

        dialog_id = str(uuid.uuid4())
        self.dialog_collection.insert_one({
            "_id": dialog_id,
            "user_id": user_id,
            "chat_mode": self.get_user_attribute(user_id, "current_chat_mode"),
            "start_time": datetime.now(),
            "model": self.get_user_attribute(user_id, "current_model"),
            "messages": []
        })

        self.user_collection.update_one({"_id": user_id}, {"$set": {"current_dialog_id": dialog_id}})
        return dialog_id

    def get_user_attribute(self, user_id: int, key: str):
        self.check_if_user_exists(user_id, raise_exception=True)
        user = self.user_collection.find_one({"_id": user_id})
        return user.get(key)

    def set_user_attribute(self, user_id: int, key: str, value: Any):
        self.check_if_user_exists(user_id, raise_exception=True)
        self.user_collection.update_one({"_id": user_id}, {"$set": {key: value}})

    def update_n_used_tokens(self, user_id: int, model: str, n_input_tokens: int, n_output_tokens: int):
        n_used_tokens = self.get_user_attribute(user_id, "n_used_tokens")
        if model not in n_used_tokens:
            n_used_tokens[model] = {"n_input_tokens": 0, "n_output_tokens": 0}
        
        n_used_tokens[model]["n_input_tokens"] += n_input_tokens
        n_used_tokens[model]["n_output_tokens"] += n_output_tokens
        self.set_user_attribute(user_id, "n_used_tokens", n_used_tokens)

    def get_dialog_messages(self, user_id: int, dialog_id: Optional[str] = None):
        if dialog_id is None:
            dialog_id = self.get_user_attribute(user_id, "current_dialog_id")

        dialog = self.dialog_collection.find_one({"_id": dialog_id, "user_id": user_id})
        return dialog["messages"]

    def set_dialog_messages(self, user_id: int, messages: list, dialog_id: Optional[str] = None):
        if dialog_id is None:
            dialog_id = self.get_user_attribute(user_id, "current_dialog_id")

        self.dialog_collection.update_one({"_id": dialog_id, "user_id": user_id}, {"$set": {"messages": messages}})

    # Journal entries methods
    def add_journal_entry(self, user_id: int, category: str, content: str, status: str = "active"):
        entry_id = str(uuid.uuid4())
        self.journal_collection.insert_one({
            "_id": entry_id,
            "user_id": user_id,
            "timestamp": datetime.now(),
            "category": category,
            "content": content,
            "status": status
        })
        return entry_id

    def get_journal_entries(self, user_id: int, category: str = None, status: str = None):
        query = {"user_id": user_id}
        if category is not None:
            query["category"] = category
        if status is not None:
            query["status"] = status
        return list(self.journal_collection.find(query))

    def update_journal_entry_status(self, entry_id: str, new_status: str):
        self.journal_collection.update_one({"_id": entry_id}, {"$set": {"status": new_status}})

    def archive_old_entries(self, user_id: int, days_old: int = 30):
        threshold_date = datetime.now() - timedelta(days=days_old)
        self.journal_collection.update_many(
            {"user_id": user_id, "timestamp": {"$lt": threshold_date}},
            {"$set": {"status": "archived"}}
        )
