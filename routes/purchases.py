"""
Purchase/Sales routes for web users.
Handles retrieving purchase history for authenticated users.
"""

from fastapi import APIRouter, HTTPException, Header, status
from typing import Optional, List
from datetime import datetime

from config.db_connection import DatabaseManager

router = APIRouter()


async def get_user_by_token(token: str):
    """Get user by session token."""
    pool = await DatabaseManager.get_pool()
    async with pool.acquire() as conn:
        user = await conn.fetchrow(
            """
            SELECT id, username, email
            FROM web_users
            WHERE session_token = $1 AND status = 'active'
            """,
            token
        )
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired token"
            )
        return dict(user)


@router.get("/my-purchases")
async def get_my_purchases(authorization: Optional[str] = Header(None)):
    """
    Get purchase history for the authenticated user.
    
    Returns all purchases made by the logged-in user with details including:
    - Order information (date, total, status)
    - Product details (name, quantity, price)
    - Shipping information (if applicable)
    
    Requires Authorization header with Bearer token.
    """
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid authorization header"
        )
    
    token = authorization.replace("Bearer ", "")
    current_user = await get_user_by_token(token)
    
    pool = await DatabaseManager.get_pool()
    
    async with pool.acquire() as conn:
        # Get all sales for this web user
        sales = await conn.fetch(
            """
            SELECT 
                s.id,
                s.sale_date,
                s.subtotal,
                s.tax_amount,
                s.discount,
                s.total,
                s.status,
                s.shipping_address,
                s.shipping_status,
                s.shipping_cost,
                s.payment_reference,
                s.invoice_number,
                s.notes,
                s.origin
            FROM sales s
            WHERE s.web_user_id = $1
            ORDER BY s.sale_date DESC
            """,
            current_user['id']
        )
        
        if not sales:
            return []
        
        # For each sale, get the details (products)
        purchases = []
        for sale in sales:
            sale_dict = dict(sale)
            
            # Get sale details (products)
            details = await conn.fetch(
                """
                SELECT 
                    sd.id,
                    sd.product_name,
                    sd.product_code,
                    sd.size_name,
                    sd.color_name,
                    sd.sale_price,
                    sd.quantity,
                    sd.discount_percentage,
                    sd.discount_amount,
                    sd.subtotal,
                    sd.total,
                    p.id as product_id
                FROM sales_detail sd
                LEFT JOIN products p ON sd.product_id = p.id
                WHERE sd.sale_id = $1
                """,
                sale_dict['id']
            )
            
            # Get product images for each item
            items = []
            for detail in details:
                detail_dict = dict(detail)
                
                # Get first image of the product
                if detail_dict['product_id']:
                    image = await conn.fetchrow(
                        """
                        SELECT image_url
                        FROM images
                        WHERE product_id = $1
                        LIMIT 1
                        """,
                        detail_dict['product_id']
                    )
                    detail_dict['image_url'] = image['image_url'] if image else None
                else:
                    detail_dict['image_url'] = None
                
                items.append(detail_dict)
            
            sale_dict['items'] = items
            purchases.append(sale_dict)
        
        return purchases


@router.get("/my-purchases/{purchase_id}")
async def get_purchase_detail(
    purchase_id: int,
    authorization: Optional[str] = Header(None)
):
    """
    Get detailed information about a specific purchase.
    
    - **purchase_id**: ID of the purchase to retrieve
    
    Requires Authorization header with Bearer token.
    """
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid authorization header"
        )
    
    token = authorization.replace("Bearer ", "")
    current_user = await get_user_by_token(token)
    
    pool = await DatabaseManager.get_pool()
    
    async with pool.acquire() as conn:
        # Get sale information and verify it belongs to the user
        sale = await conn.fetchrow(
            """
            SELECT 
                s.id,
                s.sale_date,
                s.subtotal,
                s.tax_amount,
                s.discount,
                s.total,
                s.status,
                s.shipping_address,
                s.shipping_status,
                s.shipping_cost,
                s.payment_reference,
                s.invoice_number,
                s.notes,
                s.origin,
                s.created_at,
                s.updated_at
            FROM sales s
            WHERE s.id = $1 AND s.web_user_id = $2
            """,
            purchase_id,
            current_user['id']
        )
        
        if not sale:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Purchase not found or does not belong to you"
            )
        
        sale_dict = dict(sale)
        
        # Get sale details (products)
        details = await conn.fetch(
            """
            SELECT 
                sd.id,
                sd.product_name,
                sd.product_code,
                sd.size_name,
                sd.color_name,
                sd.sale_price,
                sd.quantity,
                sd.discount_percentage,
                sd.discount_amount,
                sd.tax_percentage,
                sd.tax_amount,
                sd.subtotal,
                sd.total,
                p.id as product_id
            FROM sales_detail sd
            LEFT JOIN products p ON sd.product_id = p.id
            WHERE sd.sale_id = $1
            """,
            purchase_id
        )
        
        # Get product images
        items = []
        for detail in details:
            detail_dict = dict(detail)
            
            if detail_dict['product_id']:
                image = await conn.fetchrow(
                    """
                    SELECT image_url
                    FROM images
                    WHERE product_id = $1
                    LIMIT 1
                    """,
                    detail_dict['product_id']
                )
                detail_dict['image_url'] = image['image_url'] if image else None
            else:
                detail_dict['image_url'] = None
            
            items.append(detail_dict)
        
        sale_dict['items'] = items
        
        return sale_dict
