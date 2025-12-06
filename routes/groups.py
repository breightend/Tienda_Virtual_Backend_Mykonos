"""
Groups API routes - handles all group-related endpoints.
Uses PostgreSQL database for data persistence.
"""

from fastapi import APIRouter, HTTPException, status
from typing import List
from config.db_connection import db
from models.group_models import GroupResponse, GroupWithChildren
import logging

logger = logging.getLogger(__name__)

# Create the router
router = APIRouter()


@router.get("/", response_model=List[GroupResponse])
async def get_all_groups():
    """
    Get all groups from the database.
    
    Returns:
    - List of all groups with their basic information
    """
    try:
        query = """
            SELECT 
                id,
                group_name,
                parent_group_id,
                marked_as_root
            FROM groups
            ORDER BY group_name ASC
        """
        
        groups = await db.fetch_all(query)
        
        return groups
        
    except Exception as e:
        logger.error(f"Error fetching groups: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al obtener grupos: {str(e)}"
        )


@router.get("/root", response_model=List[GroupResponse])
async def get_root_groups():
    """
    Get only root groups (groups with marked_as_root = 1 or parent_group_id IS NULL).
    
    Returns:
    - List of root groups
    """
    try:
        query = """
            SELECT 
                id,
                group_name,
                parent_group_id,
                marked_as_root
            FROM groups
            WHERE marked_as_root = 1 OR parent_group_id IS NULL
            ORDER BY group_name ASC
        """
        
        groups = await db.fetch_all(query)
        
        return groups
        
    except Exception as e:
        logger.error(f"Error fetching root groups: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al obtener grupos raíz: {str(e)}"
        )


@router.get("/hierarchy", response_model=List[GroupWithChildren])
async def get_groups_hierarchy():
    """
    Get groups organized in a hierarchical structure.
    Returns root groups with their nested children.
    
    Returns:
    - List of root groups with nested children
    """
    try:
        # Get all groups
        query = """
            SELECT 
                id,
                group_name,
                parent_group_id,
                marked_as_root
            FROM groups
            ORDER BY group_name ASC
        """
        
        all_groups = await db.fetch_all(query)
        
        # Convert to dictionaries
        groups_dict = {g['id']: dict(g) for g in all_groups}
        
        # Add children array to each group
        for group in groups_dict.values():
            group['children'] = []
        
        # Build hierarchy
        root_groups = []
        for group in groups_dict.values():
            if group['parent_group_id'] is None or group['marked_as_root'] == 1:
                root_groups.append(group)
            elif group['parent_group_id'] in groups_dict:
                parent = groups_dict[group['parent_group_id']]
                parent['children'].append(group)
        
        return root_groups
        
    except Exception as e:
        logger.error(f"Error fetching groups hierarchy: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al obtener jerarquía de grupos: {str(e)}"
        )


@router.get("/{group_id}", response_model=GroupResponse)
async def get_group(group_id: int):
    """
    Get a specific group by ID.
    
    Path Parameters:
    - group_id: The ID of the group to retrieve
    
    Returns:
    - Group information
    """
    try:
        query = """
            SELECT 
                id,
                group_name,
                parent_group_id,
                marked_as_root
            FROM groups
            WHERE id = $1
        """
        
        group = await db.fetch_one(query, group_id)
        
        if group is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Grupo con ID {group_id} no encontrado"
            )
        
        return group
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching group {group_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al obtener el grupo: {str(e)}"
        )
