import os
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, EmailStr

from database import create_document, get_documents, db
from schemas import Appuser, Group, Expense

app = FastAPI(title="Expense Split Backend", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# --------------------------
# Utilities
# --------------------------

def serialize_doc(doc: Dict[str, Any]) -> Dict[str, Any]:
    """Convert Mongo document to JSON-friendly dict"""
    if not doc:
        return doc
    d = dict(doc)
    _id = d.pop("_id", None)
    if _id is not None:
        d["id"] = str(_id)
    # Convert datetimes to isoformat
    for k, v in list(d.items()):
        try:
            from datetime import datetime

            if isinstance(v, datetime):
                d[k] = v.isoformat()
        except Exception:
            pass
    return d


# --------------------------
# Health & Schema endpoints
# --------------------------

@app.get("/")
def root():
    return {"message": "Expense Split Backend Running"}


@app.get("/test")
def test_database():
    """Check DB connectivity and list collections"""
    status = {
        "backend": "✅ Running",
        "database": "❌ Not Available",
        "database_url": "❌ Not Set",
        "database_name": "❌ Not Set",
        "collections": [],
    }
    try:
        if db is not None:
            status["database"] = "✅ Connected"
            status["database_url"] = "✅ Set" if os.getenv("DATABASE_URL") else "❌ Not Set"
            status["database_name"] = db.name if hasattr(db, "name") else "(unknown)"
            try:
                status["collections"] = db.list_collection_names()
                status["database"] = "✅ Connected & Working"
            except Exception as e:
                status["database"] = f"⚠️ Connected but error: {str(e)[:80]}"
        else:
            status["database"] = "❌ Not Connected"
    except Exception as e:
        status["database"] = f"❌ Error: {str(e)[:120]}"
    return status


@app.get("/schema")
def get_schema():
    """Expose JSON Schemas for viewer & clients"""
    models = {
        "appuser": Appuser.model_json_schema(),
        "group": Group.model_json_schema(),
        "expense": Expense.model_json_schema(),
    }
    return {"models": models}


# --------------------------
# Groups
# --------------------------

class CreateGroup(BaseModel):
    name: str
    created_by: EmailStr
    members: List[EmailStr]
    default_currency: str = "USD"
    image_url: Optional[str] = None


@app.post("/groups")
def create_group(payload: CreateGroup):
    # Ensure creator included in members
    members = list(dict.fromkeys([*(payload.members or []), payload.created_by]))
    group = Group(
        name=payload.name,
        created_by=payload.created_by,
        members=members,
        default_currency=payload.default_currency,
        image_url=payload.image_url,
    )
    group_id = create_document("group", group)
    return {"id": group_id}


@app.get("/groups")
def list_groups(member: Optional[EmailStr] = Query(None, description="Filter by member email")):
    filt: Dict[str, Any] = {}
    if member:
        filt = {"members": {"$in": [member]}}
    docs = get_documents("group", filt)
    return [serialize_doc(d) for d in docs]


# --------------------------
# Expenses
# --------------------------

class CreateExpense(BaseModel):
    group_id: str
    description: str
    amount: float
    currency: str = "USD"
    paid_by: EmailStr
    date: Optional[str] = None  # ISO string
    splits: Expense.model_fields["splits"].annotation  # reuse type from schema
    notes: Optional[str] = None


@app.post("/expenses")
def create_expense(payload: CreateExpense):
    # Basic validation: amount > 0
    if payload.amount <= 0:
        raise HTTPException(status_code=400, detail="Amount must be greater than 0")

    # Construct Expense model (pydantic will validate splits)
    expense = Expense(
        group_id=payload.group_id,
        description=payload.description,
        amount=payload.amount,
        currency=payload.currency,
        paid_by=payload.paid_by,
        date=None,
        splits=payload.splits,
        notes=payload.notes,
    )
    eid = create_document("expense", expense)
    return {"id": eid}


@app.get("/expenses")
def list_expenses(group_id: Optional[str] = Query(None, description="Filter by group id")):
    filt: Dict[str, Any] = {}
    if group_id:
        filt = {"group_id": group_id}
    docs = get_documents("expense", filt)
    return [serialize_doc(d) for d in docs]


if __name__ == "__main__":
    import uvicorn

    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
