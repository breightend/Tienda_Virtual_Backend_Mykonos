"""
Group models for Pydantic validation.
"""

from pydantic import BaseModel
from typing import Optional, List


class GroupBase(BaseModel):
    """Base group model with common fields."""
    group_name: str
    parent_group_id: Optional[int] = None
    marked_as_root: int = 0


class GroupResponse(GroupBase):
    """Group response model with ID."""
    id: int
    
    class Config:
        from_attributes = True


class GroupWithChildren(GroupResponse):
    """Group with nested children groups."""
    children: List['GroupResponse'] = []
    
    class Config:
        from_attributes = True
