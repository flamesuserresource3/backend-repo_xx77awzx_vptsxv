"""
Database Schemas for Expense Splitting App

Each Pydantic model represents a MongoDB collection. The collection name
is the lowercase of the class name (e.g., Group -> "group").

These are used for validation and for the database viewer.
"""
from __future__ import annotations

from typing import List, Optional, Literal
from pydantic import BaseModel, Field, EmailStr
from datetime import datetime


class Appuser(BaseModel):
    """
    Users of the app
    Collection: "appuser"
    """
    name: str = Field(..., description="Full name")
    email: EmailStr = Field(..., description="Unique email address")
    avatar_url: Optional[str] = Field(None, description="Profile image URL")
    default_currency: str = Field("USD", description="Preferred currency code")
    locale: str = Field("en", description="Preferred locale for formatting")


class Group(BaseModel):
    """
    Group of people who share expenses
    Collection: "group"
    """
    name: str = Field(..., description="Group name")
    created_by: EmailStr = Field(..., description="Creator's email")
    members: List[EmailStr] = Field(..., description="Member emails, including creator")
    default_currency: str = Field("USD", description="Default currency for the group")
    image_url: Optional[str] = Field(None, description="Group cover image")


class SplitItem(BaseModel):
    user: EmailStr = Field(..., description="User responsible for this share")
    type: Literal["equal", "exact", "percentage"] = Field(
        "equal", description="Split type"
    )
    share: float = Field(
        0, ge=0, description="Share amount (exact) or percent (percentage)"
    )


class Expense(BaseModel):
    """
    Expense added to a group
    Collection: "expense"
    """
    group_id: str = Field(..., description="Associated group id")
    description: str = Field(..., description="What was purchased")
    amount: float = Field(..., gt=0, description="Total amount of the expense")
    currency: str = Field("USD", description="Currency code for the expense")
    paid_by: EmailStr = Field(..., description="Who paid")
    date: Optional[datetime] = Field(None, description="When the expense happened")
    splits: List[SplitItem] = Field(
        default_factory=list, description="How the expense is split among members"
    )
    notes: Optional[str] = Field(None, description="Optional notes")


# You can extend with Settlement models later if needed
