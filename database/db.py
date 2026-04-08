import firebase_admin
from firebase_admin import credentials, firestore
import datetime
import logging

logger = logging.getLogger(__name__)

# Initialize Firebase using Application Default Credentials
if not firebase_admin._apps:
    firebase_admin.initialize_app()

db = firestore.client()

# ── Tasks ─────────────────────────────────────────────────────────────────────
def add_task(task: str, due_date=None, status="pending"):
    task_ref = db.collection("tasks").document()
    data = {
        "id": task_ref.id,
        "task": task,
        "due_date": due_date,
        "status": status,
        "created_at": datetime.datetime.now().isoformat()
    }
    task_ref.set(data)
    return data

def get_tasks(status=None):
    docs = db.collection("tasks")
    if status:
        docs = docs.where("status", "==", status)
    return [doc.to_dict() for doc in docs.stream()]

def update_task_status(task_id, status):
    # ADK uses numeric IDs in prompts; Firestore uses strings. 
    # We query the 'id' field to match.
    docs = db.collection("tasks").where("id", "==", str(task_id)).limit(1).get()
    if not docs:
        raise ValueError(f"Task {task_id} not found")
    docs[0].reference.update({"status": status})
    return docs[0].to_dict()

# ── Notes ─────────────────────────────────────────────────────────────────────
def add_note(content: str):
    note_ref = db.collection("notes").document()
    data = {
        "id": note_ref.id,
        "content": content,
        "created_at": datetime.datetime.now().isoformat()
    }
    note_ref.set(data)
    return data

def get_notes(limit=20):
    docs = db.collection("notes").order_by("created_at", direction=firestore.Query.DESCENDING).limit(limit)
    return [doc.to_dict() for doc in docs.stream()]