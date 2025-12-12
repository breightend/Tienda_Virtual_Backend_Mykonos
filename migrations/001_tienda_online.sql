BEGIN;

-- ---------------------------------------------------------
-- 1. CREACIÓN DE NUEVAS TABLAS (Web & Carrito)
-- ---------------------------------------------------------

-- Tabla de Usuarios Web
CREATE TABLE IF NOT EXISTS web_users (
    id SERIAL PRIMARY KEY,
    username TEXT UNIQUE,
    fullname TEXT,
    password TEXT,
    email TEXT,
    phone TEXT,
    domicilio TEXT,
    cuit TEXT UNIQUE,
    role TEXT,
    status TEXT,
    session_token TEXT,
    email_verified BOOLEAN DEFAULT FALSE,
    verification_token TEXT,
    profile_image_url TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Tabla de Carritos (Cabecera)
CREATE TABLE IF NOT EXISTS web_carts (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_web_carts_user FOREIGN KEY (user_id) REFERENCES web_users(id)
);

-- Tabla de Items del Carrito (Detalle)
CREATE TABLE IF NOT EXISTS web_cart_items (
    id SERIAL PRIMARY KEY,
    cart_id INTEGER NOT NULL,
    product_id INTEGER NOT NULL,
    variant_id INTEGER NOT NULL, -- Importante para stock
    quantity INTEGER NOT NULL CHECK (quantity > 0),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_cart_items_cart FOREIGN KEY (cart_id) REFERENCES web_carts(id),
    CONSTRAINT fk_cart_items_product FOREIGN KEY (product_id) REFERENCES products(id),
    CONSTRAINT fk_cart_items_variant FOREIGN KEY (variant_id) REFERENCES warehouse_stock_variants(id)
);

-- Tabla de Historial de seguimiento de ventas
CREATE TABLE IF NOT EXISTS sales_tracking_history (
    id SERIAL PRIMARY KEY,
    sale_id INTEGER NOT NULL,
    status TEXT NOT NULL,
    description TEXT,
    location TEXT,
    changed_by_user_id INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_sales_tracking_history_sale FOREIGN KEY (sale_id) REFERENCES sales(id),
    CONSTRAINT fk_sales_tracking_history_user FOREIGN KEY (changed_by_user_id) REFERENCES users(id)
);

-- ---------------------------------------------------------
-- 2. MODIFICACIÓN DE LA TABLA PRODUCTS
-- ---------------------------------------------------------

-- Agregar columnas para la tienda online
ALTER TABLE products ADD COLUMN IF NOT EXISTS en_tienda_online BOOLEAN DEFAULT FALSE;
ALTER TABLE products ADD COLUMN IF NOT EXISTS nombre_web TEXT;
ALTER TABLE products ADD COLUMN IF NOT EXISTS descripcion_web TEXT;
ALTER TABLE products ADD COLUMN IF NOT EXISTS slug TEXT;
ALTER TABLE products ADD COLUMN IF NOT EXISTS precio_web NUMERIC(10,2);

-- Crear restricción de unicidad para el slug (para URLs amigables)
ALTER TABLE products DROP CONSTRAINT IF EXISTS uq_products_slug;
ALTER TABLE products ADD CONSTRAINT uq_products_slug UNIQUE (slug);

-- Eliminar restricción de unicidad para el barcode de variantes
ALTER TABLE warehouse_stock_variants DROP CONSTRAINT IF EXISTS uq_variant_barcode;

-- Agregar restricción de unicidad para variantes por sucursal
ALTER TABLE warehouse_stock_variants 
ADD CONSTRAINT unique_variant_per_branch 
UNIQUE (product_id, size_id, color_id, branch_id);

-- Borrar la columna images_ids (si existía)
ALTER TABLE products DROP COLUMN IF EXISTS images_ids;

-- ---------------------------------------------------------
-- 3. MODIFICACIÓN DE LA TABLA SALES (Ventas)
-- ---------------------------------------------------------

ALTER TABLE sales ADD COLUMN IF NOT EXISTS origin TEXT DEFAULT 'local';
ALTER TABLE sales ADD COLUMN IF NOT EXISTS shipping_address TEXT;
ALTER TABLE sales ADD COLUMN IF NOT EXISTS shipping_status TEXT;
ALTER TABLE sales ADD COLUMN IF NOT EXISTS external_payment_id TEXT;
ALTER TABLE sales ADD COLUMN IF NOT EXISTS shipping_cost NUMERIC(10,2) DEFAULT 0;
ALTER TABLE sales ADD COLUMN IF NOT EXISTS web_user_id INTEGER;
ALTER TABLE sales ADD COLUMN IF NOT EXISTS delivery_type VARCHAR(20) DEFAULT 'envio';

-- Agregar la Foreign Key hacia el usuario web
ALTER TABLE sales 
    DROP CONSTRAINT IF EXISTS fk_sales_web_user;
    
ALTER TABLE sales 
    ADD CONSTRAINT fk_sales_web_user 
    FOREIGN KEY (web_user_id) REFERENCES web_users(id);

-- ---------------------------------------------------------
-- 4. ARREGLO DE LA TABLA IMAGES
-- ---------------------------------------------------------

-- Agregar la columna de URL
ALTER TABLE images ADD COLUMN IF NOT EXISTS image_url TEXT;

-- Quitar la restricción NOT NULL de la columna binaria (BYTEA)
ALTER TABLE images ALTER COLUMN image_data DROP NOT NULL;

COMMIT;
