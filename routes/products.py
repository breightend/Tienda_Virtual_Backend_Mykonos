"""
Products API routes - handles all product-related endpoints.
Uses PostgreSQL database for data persistence.
"""

from fastapi import APIRouter, HTTPException, status
from typing import List, Optional
from config.db_connection import db
from models.product_models import (
    ProductCreate,
    ProductUpdate,
    ProductResponse,
    ProductSimple,
    ProductWithImages,
    OnlineStoreProduct,
    ProductImage,
    AddProductImage,
    ProductDetail
)
import logging

logger = logging.getLogger(__name__)

# Create the router
router = APIRouter()


# --- VIRTUAL STORE ENDPOINTS ---

@router.get("/productos", response_model=List[OnlineStoreProduct])
async def get_all_productos():
    """
    Get ALL products available in the online store (no limits).
    Only returns products where en_tienda_online = TRUE.
    
    Returns:
    - List of all online store products with images, stock, and variants
    """
    try:
        # Get all products
        query = """
            SELECT 
                p.id,
                p.nombre_web,
                p.descripcion_web,
                p.precio_web,
                p.slug,
                COALESCE(g.group_name, 'Sin categoría') as category,
                COALESCE(
                    ARRAY_AGG(DISTINCT i.image_url) FILTER (WHERE i.image_url IS NOT NULL),
                    ARRAY[]::TEXT[]
                ) as images,
                COALESCE(SUM(wsv.quantity), 0) as stock_disponible
            FROM products p
            LEFT JOIN groups g ON p.group_id = g.id
            LEFT JOIN images i ON i.product_id = p.id
            LEFT JOIN warehouse_stock_variants wsv ON wsv.product_id = p.id
            WHERE p.en_tienda_online = TRUE
            GROUP BY p.id, g.group_name
            ORDER BY p.id DESC
        """
        
        products = await db.fetch_all(query)
        
        # Get variants for each product
        result = []
        for product in products:
            product_dict = dict(product)
            
            # Get variants for this product
            variants_query = """
                SELECT 
                    wsv.id as variant_id,
                    s.size_name as talle,
                    c.color_name as color,
                    c.color_hex,
                    wsv.quantity as stock,
                    wsv.variant_barcode as barcode
                FROM warehouse_stock_variants wsv
                LEFT JOIN sizes s ON wsv.size_id = s.id
                LEFT JOIN colors c ON wsv.color_id = c.id
                WHERE wsv.product_id = $1 AND wsv.quantity > 0
                ORDER BY s.size_name, c.color_name
            """
            variants = await db.fetch_all(variants_query, product['id'])
            
            product_dict['variantes'] = [
                {
                    "variant_id": v['variant_id'],
                    "talle": v['talle'],
                    "color": v['color'],
                    "color_hex": v['color_hex'],
                    "stock": v['stock'],
                    "barcode": v['barcode']
                } 
                for v in variants
            ]
            
            result.append(product_dict)
        
        return result
        
    except Exception as e:
        logger.error(f"Error fetching productos: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al obtener productos: {str(e)}"
        )


@router.get("/productsByGroup/{groupName}", response_model=List[OnlineStoreProduct])
async def get_productos_by_group(groupName: str):
    """
    Get products filtered by group name for the online store.
    Includes products from the specified group AND all its descendant groups (children, grandchildren, etc.).
    Only returns products where en_tienda_online = TRUE.
    
    Path Parameters:
    - groupName: The name of the group to filter by
    
    Returns:
    - List of online store products in the specified group and all descendant groups with images, stock, and variants
    
    Example:
    - If "Remeras" is selected, returns products from "Remeras", "Remeras Musculosas", "Remeras Mangas Largas", etc.
    - If "Remeras Mangas Largas" is selected, returns products from "Remeras Mangas Largas" and its children only
    """
    try:
        # First, get all descendant group IDs using recursive CTE
        descendant_groups_query = """
            WITH RECURSIVE group_tree AS (
                -- Base case: select the requested group
                SELECT id, group_name, parent_group_id
                FROM groups
                WHERE group_name = $1
                
                UNION ALL
                
                -- Recursive case: select all children
                SELECT g.id, g.group_name, g.parent_group_id
                FROM groups g
                INNER JOIN group_tree gt ON g.parent_group_id = gt.id
            )
            SELECT id FROM group_tree
        """
        
        descendant_groups = await db.fetch_all(descendant_groups_query, groupName)
        
        if not descendant_groups:
            # Group not found, return empty list
            return []
        
        # Extract group IDs
        group_ids = [g['id'] for g in descendant_groups]
        
        # Get products from all descendant groups
        # Build the query with dynamic IN clause
        placeholders = ', '.join([f'${i+1}' for i in range(len(group_ids))])
        
        query = f"""
            SELECT 
                p.id,
                p.nombre_web,
                p.descripcion_web,
                p.precio_web,
                p.slug,
                COALESCE(g.group_name, 'Sin categoría') as category,
                COALESCE(
                    ARRAY_AGG(DISTINCT i.image_url) FILTER (WHERE i.image_url IS NOT NULL),
                    ARRAY[]::TEXT[]
                ) as images,
                COALESCE(SUM(wsv.quantity), 0) as stock_disponible
            FROM products p
            LEFT JOIN groups g ON p.group_id = g.id
            LEFT JOIN images i ON i.product_id = p.id
            LEFT JOIN warehouse_stock_variants wsv ON wsv.product_id = p.id
            WHERE p.en_tienda_online = TRUE AND p.group_id IN ({placeholders})
            GROUP BY p.id, g.group_name
            ORDER BY p.id DESC
        """
        
        products = await db.fetch_all(query, *group_ids)
        
        # Get variants for each product
        result = []
        for product in products:
            product_dict = dict(product)
            
            # Get variants for this product
            variants_query = """
                SELECT 
                    wsv.id as variant_id,
                    s.size_name as talle,
                    c.color_name as color,
                    c.color_hex,
                    wsv.quantity as stock,
                    wsv.variant_barcode as barcode
                FROM warehouse_stock_variants wsv
                LEFT JOIN sizes s ON wsv.size_id = s.id
                LEFT JOIN colors c ON wsv.color_id = c.id
                WHERE wsv.product_id = $1 AND wsv.quantity > 0
                ORDER BY s.size_name, c.color_name
            """
            variants = await db.fetch_all(variants_query, product['id'])
            
            product_dict['variantes'] = [
                {
                    "variant_id": v['variant_id'],
                    "talle": v['talle'],
                    "color": v['color'],
                    "color_hex": v['color_hex'],
                    "stock": v['stock'],
                    "barcode": v['barcode']
                } 
                for v in variants
            ]
            
            result.append(product_dict)
        
        return result
        
    except Exception as e:
        logger.error(f"Error fetching productos by group {groupName}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al obtener productos del grupo: {str(e)}"
        )



@router.get("/{product_id}", response_model=ProductDetail)
async def get_product(product_id: int):
    """
    Get complete information for a specific product by ID.
    Includes all details: images, colors, sizes, variants, and stock.
    
    Path Parameters:
    - product_id: The ID of the product to retrieve
    
    Returns:
    - Complete product information with all variants and stock details
    """
    try:
        # Get basic product info with images
        product_query = """
            SELECT 
                p.id,
                p.nombre_web,
                p.descripcion_web,
                p.precio_web,
                p.slug,
                COALESCE(g.group_name, 'Sin categoría') as category,
                COALESCE(
                    ARRAY_AGG(DISTINCT i.image_url) FILTER (WHERE i.image_url IS NOT NULL),
                    ARRAY[]::TEXT[]
                ) as images,
                COALESCE(SUM(wsv.quantity), 0) as stock_disponible
            FROM products p
            LEFT JOIN groups g ON p.group_id = g.id
            LEFT JOIN images i ON i.product_id = p.id
            LEFT JOIN warehouse_stock_variants wsv ON wsv.product_id = p.id
            WHERE p.id = $1 AND p.en_tienda_online = TRUE
            GROUP BY p.id, g.group_name
        """
        
        product = await db.fetch_one(product_query, product_id)
        
        if product is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Producto con ID {product_id} no encontrado en la tienda online"
            )
        
        # Get colors for this product
        colors_query = """
            SELECT DISTINCT c.id, c.color_name, c.color_hex
            FROM product_colors pc
            JOIN colors c ON pc.color_id = c.id
            WHERE pc.product_id = $1
            ORDER BY c.color_name
        """
        colors = await db.fetch_all(colors_query, product_id)
        
        # Get sizes for this product
        sizes_query = """
            SELECT DISTINCT s.size_name
            FROM product_sizes ps
            JOIN sizes s ON ps.size_id = s.id
            WHERE ps.product_id = $1
            ORDER BY s.size_name
        """
        sizes = await db.fetch_all(sizes_query, product_id)
        
        # Get variants with stock
        variants_query = """
            SELECT 
                wsv.id as variant_id,
                s.size_name as talle,
                c.color_name as color,
                c.color_hex,
                wsv.quantity as stock,
                wsv.variant_barcode as barcode
            FROM warehouse_stock_variants wsv
            LEFT JOIN sizes s ON wsv.size_id = s.id
            LEFT JOIN colors c ON wsv.color_id = c.id
            WHERE wsv.product_id = $1 AND wsv.quantity > 0
            ORDER BY s.size_name, c.color_name
        """
        variants = await db.fetch_all(variants_query, product_id)
        
        # Build response
        product_dict = dict(product)
        product_dict['colores'] = [
            {"id": c['id'], "nombre": c['color_name'], "hex": c['color_hex']} 
            for c in colors
        ]
        product_dict['talles'] = [s['size_name'] for s in sizes]
        product_dict['variantes'] = [
            {
                "variant_id": v['variant_id'],
                "talle": v['talle'],
                "color": v['color'],
                "color_hex": v['color_hex'],
                "stock": v['stock'],
                "barcode": v['barcode']
            } 
            for v in variants
        ]
        
        return product_dict
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching product {product_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al obtener el producto: {str(e)}"
        )


@router.post("/", response_model=ProductResponse, status_code=status.HTTP_201_CREATED)
async def create_product(product: ProductCreate):
    """
    Create a new product in the database.
    
    Request Body:
    - ProductCreate model with all product details
    """
    try:
        query = """
            INSERT INTO products (
                product_name, description, cost, sale_price, provider_code,
                group_id, provider_id, brand_id, tax, discount,
                original_price, discount_percentage, discount_amount,
                has_discount, comments, state, 
                en_tienda_online, nombre_web, descripcion_web, slug, precio_web,
                creation_date
            )
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16, 
                    $17, $18, $19, $20, $21, CURRENT_TIMESTAMP)
            RETURNING id, product_name, description, cost, sale_price, provider_code,
                      group_id, provider_id, brand_id, tax, discount,
                      original_price, discount_percentage, discount_amount,
                      has_discount, comments, state, 
                      en_tienda_online, nombre_web, descripcion_web, slug, precio_web,
                      creation_date
        """
        
        result = await db.fetch_one(
            query,
            product.product_name,
            product.description,
            product.cost,
            product.sale_price,
            product.provider_code,
            product.group_id,
            product.provider_id,
            product.brand_id,
            product.tax,
            product.discount,
            product.original_price,
            product.discount_percentage,
            product.discount_amount,
            product.has_discount,
            product.comments,
            product.state,
            product.en_tienda_online,
            product.nombre_web,
            product.descripcion_web,
            product.slug,
            product.precio_web
        )
        
        if result is None:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Error al crear el producto"
            )
        
        return result
        
    except Exception as e:
        logger.error(f"Error creating product: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al crear el producto: {str(e)}"
        )


@router.put("/{product_id}", response_model=ProductResponse)
async def update_product(product_id: int, product: ProductUpdate):
    """
    Update an existing product.
    
    Path Parameters:
    - product_id: The ID of the product to update
    
    Request Body:
    - ProductUpdate model with fields to update (all optional)
    """
    try:
        # First, check if product exists
        existing = await db.fetch_one("SELECT id FROM products WHERE id = $1", product_id)
        if existing is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Producto con ID {product_id} no encontrado"
            )
        
        # Build dynamic update query based on provided fields
        update_fields = []
        params = []
        param_count = 1
        
        for field, value in product.dict(exclude_unset=True).items():
            update_fields.append(f"{field} = ${param_count}")
            params.append(value)
            param_count += 1
        
        if not update_fields:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No se proporcionaron campos para actualizar"
            )
        
        # Add last_modified_date
        update_fields.append(f"last_modified_date = CURRENT_TIMESTAMP")
        
        # Add product_id as the last parameter
        params.append(product_id)
        
        query = f"""
            UPDATE products
            SET {', '.join(update_fields)}
            WHERE id = ${param_count}
            RETURNING id, product_name, description, cost, sale_price, provider_code,
                      group_id, provider_id, brand_id, tax, discount,
                      original_price, discount_percentage, discount_amount,
                      has_discount, comments, state, 
                      en_tienda_online, nombre_web, descripcion_web, slug, precio_web,
                      creation_date, last_modified_date
        """
        
        result = await db.fetch_one(query, *params)
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating product {product_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al actualizar el producto: {str(e)}"
        )


@router.delete("/{product_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_product(product_id: int):
    """
    Delete a product from the database.
    
    Path Parameters:
    - product_id: The ID of the product to delete
    """
    try:
        # Check if product exists
        existing = await db.fetch_one("SELECT id FROM products WHERE id = $1", product_id)
        if existing is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Producto con ID {product_id} no encontrado"
            )
        
        # Delete the product
        await db.execute("DELETE FROM products WHERE id = $1", product_id)
        
        return None
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting product {product_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al eliminar el producto: {str(e)}"
        )


# --- ONLINE STORE ENDPOINTS ---

@router.get("/online-store", response_model=List[OnlineStoreProduct])
async def get_online_store_products(
    category: Optional[str] = None,
    limit: Optional[int] = 50,
    offset: Optional[int] = 0
):
    """
    Get products available in the online store.
    Only returns products where en_tienda_online = TRUE and with available stock.
    
    Query Parameters:
    - category: Filter by product group name (optional)
    - limit: Maximum number of products to return (default: 50)
    - offset: Number of products to skip (default: 0)
    """
    try:
        query = """
            SELECT 
                p.id,
                p.nombre_web,
                p.descripcion_web,
                p.precio_web,
                p.slug,
                COALESCE(g.group_name, 'Sin categoría') as category,
                COALESCE(
                    ARRAY_AGG(i.image_url) FILTER (WHERE i.image_url IS NOT NULL),
                    ARRAY[]::TEXT[]
                ) as images,
                COALESCE(SUM(wsv.quantity), 0) as stock_disponible
            FROM products p
            LEFT JOIN groups g ON p.group_id = g.id
            LEFT JOIN images i ON i.product_id = p.id
            LEFT JOIN warehouse_stock_variants wsv ON wsv.product_id = p.id
            WHERE p.en_tienda_online = TRUE
        """
        params = []
        param_count = 1
        
        if category:
            query += f" AND g.group_name ILIKE ${param_count}"
            params.append(f"%{category}%")
            param_count += 1
        
        query += f"""
            GROUP BY p.id, g.group_name
            HAVING COALESCE(SUM(wsv.quantity), 0) > 0
            ORDER BY p.id DESC 
            LIMIT ${param_count} OFFSET ${param_count + 1}
        """
        params.extend([limit, offset])
        
        products = await db.fetch_all(query, *params)
        
        return products
        
    except Exception as e:
        logger.error(f"Error fetching online store products: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al obtener productos de la tienda online: {str(e)}"
        )


@router.get("/online-store/{slug}", response_model=OnlineStoreProduct)
async def get_product_by_slug(slug: str):
    """
    Get a product by its slug for the online store.
    
    Path Parameters:
    - slug: The URL-friendly slug of the product
    """
    try:
        query = """
            SELECT 
                p.id,
                p.nombre_web,
                p.descripcion_web,
                p.precio_web,
                p.slug,
                COALESCE(g.group_name, 'Sin categoría') as category,
                COALESCE(
                    ARRAY_AGG(i.image_url) FILTER (WHERE i.image_url IS NOT NULL),
                    ARRAY[]::TEXT[]
                ) as images,
                COALESCE(SUM(wsv.quantity), 0) as stock_disponible
            FROM products p
            LEFT JOIN groups g ON p.group_id = g.id
            LEFT JOIN images i ON i.product_id = p.id
            LEFT JOIN warehouse_stock_variants wsv ON wsv.product_id = p.id
            WHERE p.slug = $1 AND p.en_tienda_online = TRUE
            GROUP BY p.id, g.group_name
        """
        
        product = await db.fetch_one(query, slug)
        
        if product is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Producto con slug '{slug}' no encontrado en la tienda online"
            )
        
        return product
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching product by slug {slug}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al obtener el producto: {str(e)}"
        )


# --- IMAGE MANAGEMENT ENDPOINTS ---

@router.post("/{product_id}/images", response_model=ProductImage, status_code=status.HTTP_201_CREATED)
async def add_product_image(product_id: int, image_data: AddProductImage):
    """
    Add an image URL to a product.
    
    Path Parameters:
    - product_id: The ID of the product
    
    Request Body:
    - image_url: The URL of the image to add
    """
    try:
        # Check if product exists
        existing = await db.fetch_one("SELECT id FROM products WHERE id = $1", product_id)
        if existing is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Producto con ID {product_id} no encontrado"
            )
        
        # Insert the image
        query = """
            INSERT INTO images (product_id, image_url)
            VALUES ($1, $2)
            RETURNING id, image_url, product_id
        """
        
        result = await db.fetch_one(query, product_id, image_data.image_url)
        
        if result is None:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Error al agregar la imagen"
            )
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error adding image to product {product_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al agregar la imagen: {str(e)}"
        )


@router.delete("/images/{image_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_product_image(image_id: int):
    """
    Delete an image from a product.
    
    Path Parameters:
    - image_id: The ID of the image to delete
    """
    try:
        # Check if image exists
        existing = await db.fetch_one("SELECT id FROM images WHERE id = $1", image_id)
        if existing is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Imagen con ID {image_id} no encontrada"
            )
        
        # Delete the image
        await db.execute("DELETE FROM images WHERE id = $1", image_id)
        
        return None
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting image {image_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al eliminar la imagen: {str(e)}"
        )