#!/usr/bin/env python3
"""
Script para insertar datos de prueba en la base de datos
- Usuarios web
- Productos marcados como en_tienda_online
"""

import asyncio
import asyncpg
import os
from dotenv import load_dotenv
import bcrypt

# Cargar variables de entorno
load_dotenv()

# Configuración de la base de datos
DB_CONFIG = {
    "host": os.getenv("DB_HOST", "localhost"),
    "port": int(os.getenv("DB_PORT", "5432")),
    "database": os.getenv("DB_NAME", "mykonos_db"),
    "user": os.getenv("DB_USER", "postgres"),
    "password": os.getenv("DB_PASSWORD"),
}


def hash_password(password: str) -> str:
    """Hash a password using bcrypt"""
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
    return hashed.decode('utf-8')


async def verify_migration():
    """Verifica que las migraciones se hayan aplicado correctamente"""
    print("=" * 60)
    print("🔍 VERIFICANDO MIGRACIONES")
    print("=" * 60)
    
    conn = await asyncpg.connect(**DB_CONFIG)
    
    # Verificar nuevas tablas
    print("\n📊 Verificando nuevas tablas...")
    tables = ['web_users', 'web_carts', 'web_cart_items', 'sales_tracking_history']
    
    for table in tables:
        exists = await conn.fetchval(
            """
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_name = $1
            )
            """,
            table
        )
        status = "✅" if exists else "❌"
        print(f"   {status} Tabla '{table}'")
    
    # Verificar nuevas columnas en products
    print("\n📊 Verificando columnas en 'products'...")
    product_columns = ['en_tienda_online', 'nombre_web', 'descripcion_web', 'slug']
    
    for column in product_columns:
        exists = await conn.fetchval(
            """
            SELECT EXISTS (
                SELECT FROM information_schema.columns 
                WHERE table_name = 'products' 
                AND column_name = $1
            )
            """,
            column
        )
        status = "✅" if exists else "❌"
        print(f"   {status} Columna 'products.{column}'")
    
    # Verificar nuevas columnas en sales
    print("\n📊 Verificando columnas en 'sales'...")
    sales_columns = ['origin', 'shipping_address', 'web_user_id', 'delivery_type']
    
    for column in sales_columns:
        exists = await conn.fetchval(
            """
            SELECT EXISTS (
                SELECT FROM information_schema.columns 
                WHERE table_name = 'sales' 
                AND column_name = $1
            )
            """,
            column
        )
        status = "✅" if exists else "❌"
        print(f"   {status} Columna 'sales.{column}'")
    
    await conn.close()
    print("\n✅ Verificación de migraciones completada")


async def insert_test_users():
    """Inserta usuarios de prueba en web_users"""
    print("\n" + "=" * 60)
    print("👥 INSERTANDO USUARIOS DE PRUEBA")
    print("=" * 60)
    
    conn = await asyncpg.connect(**DB_CONFIG)
    
    users = [
        {
            "username": "juan.perez",
            "fullname": "Juan Pérez",
            "email": "juan.perez@example.com",
            "password": hash_password("password123"),
            "phone": "+54 11 1234-5678",
            "domicilio": "Av. Corrientes 1234, CABA",
            "cuit": "20-12345678-9",
            "role": "customer",
            "status": "active",
            "email_verified": True
        },
        {
            "username": "maria.garcia",
            "fullname": "María García",
            "email": "maria.garcia@example.com",
            "password": hash_password("password123"),
            "phone": "+54 11 8765-4321",
            "domicilio": "Av. Santa Fe 5678, CABA",
            "cuit": "27-87654321-3",
            "role": "customer",
            "status": "active",
            "email_verified": True
        },
        {
            "username": "carlos.rodriguez",
            "fullname": "Carlos Rodríguez",
            "email": "carlos.rodriguez@example.com",
            "password": hash_password("password123"),
            "phone": "+54 11 5555-6666",
            "domicilio": "Av. Cabildo 9012, CABA",
            "cuit": "20-55556666-7",
            "role": "customer",
            "status": "active",
            "email_verified": False
        }
    ]
    
    for user in users:
        try:
            await conn.execute(
                """
                INSERT INTO web_users (
                    username, fullname, email, password, phone, 
                    domicilio, cuit, role, status, email_verified
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
                ON CONFLICT (username) DO NOTHING
                """,
                user["username"], user["fullname"], user["email"], 
                user["password"], user["phone"], user["domicilio"],
                user["cuit"], user["role"], user["status"], user["email_verified"]
            )
            print(f"   ✅ Usuario creado: {user['username']} ({user['fullname']})")
        except Exception as e:
            print(f"   ⚠️  Error creando {user['username']}: {e}")
    
    # Mostrar usuarios creados
    users_count = await conn.fetchval("SELECT COUNT(*) FROM web_users")
    print(f"\n📊 Total de usuarios web: {users_count}")
    
    await conn.close()


async def update_products_for_online_store():
    """Actualiza productos para que estén disponibles en la tienda online"""
    print("\n" + "=" * 60)
    print("🛍️  CONFIGURANDO PRODUCTOS PARA TIENDA ONLINE")
    print("=" * 60)
    
    conn = await asyncpg.connect(**DB_CONFIG)
    
    # Obtener algunos productos existentes
    products = await conn.fetch(
        """
        SELECT id, product_name, description 
        FROM products 
        LIMIT 10
        """
    )
    
    if not products:
        print("   ⚠️  No hay productos en la base de datos")
        await conn.close()
        return
    
    print(f"\n📦 Actualizando {len(products)} productos...")
    
    for product in products:
        # Crear slug a partir del nombre
        slug = product['product_name'].lower().replace(' ', '-').replace('/', '-')
        slug = ''.join(c for c in slug if c.isalnum() or c == '-')
        
        try:
            await conn.execute(
                """
                UPDATE products 
                SET 
                    en_tienda_online = TRUE,
                    nombre_web = $1,
                    descripcion_web = $2,
                    slug = $3
                WHERE id = $4
                """,
                product['product_name'],
                product['description'] or f"Descripción de {product['product_name']}",
                f"{slug}-{product['id']}",  # Agregar ID para evitar duplicados
                product['id']
            )
            print(f"   ✅ Producto actualizado: {product['product_name']}")
        except Exception as e:
            print(f"   ⚠️  Error actualizando producto {product['id']}: {e}")
    
    # Mostrar estadísticas
    online_count = await conn.fetchval(
        "SELECT COUNT(*) FROM products WHERE en_tienda_online = TRUE"
    )
    total_count = await conn.fetchval("SELECT COUNT(*) FROM products")
    
    print(f"\n📊 Productos en tienda online: {online_count}/{total_count}")
    
    # Mostrar algunos productos online
    print("\n📋 Productos disponibles online:")
    online_products = await conn.fetch(
        """
        SELECT id, nombre_web, slug, en_tienda_online
        FROM products 
        WHERE en_tienda_online = TRUE
        LIMIT 5
        """
    )
    
    for p in online_products:
        print(f"   • ID {p['id']}: {p['nombre_web']} (slug: {p['slug']})")
    
    await conn.close()


async def show_database_summary():
    """Muestra un resumen del estado de la base de datos"""
    print("\n" + "=" * 60)
    print("📊 RESUMEN DE LA BASE DE DATOS")
    print("=" * 60)
    
    conn = await asyncpg.connect(**DB_CONFIG)
    
    # Contar registros en tablas principales
    tables_info = [
        ("products", "Productos"),
        ("web_users", "Usuarios Web"),
        ("web_carts", "Carritos"),
        ("web_cart_items", "Items en Carritos"),
        ("sales", "Ventas"),
        ("sales_tracking_history", "Historial de Seguimiento"),
    ]
    
    print("\n📈 Registros por tabla:")
    for table, label in tables_info:
        try:
            count = await conn.fetchval(f"SELECT COUNT(*) FROM {table}")
            print(f"   • {label:30} {count:>5} registros")
        except Exception as e:
            print(f"   • {label:30} ❌ Error: {e}")
    
    # Productos online
    try:
        online_count = await conn.fetchval(
            "SELECT COUNT(*) FROM products WHERE en_tienda_online = TRUE"
        )
        print(f"\n🛍️  Productos en tienda online: {online_count}")
    except:
        pass
    
    await conn.close()


async def main():
    """Función principal"""
    print("=" * 60)
    print("🚀 SCRIPT DE DATOS DE PRUEBA - MYKONOS")
    print("=" * 60)
    
    try:
        # 1. Verificar migraciones
        await verify_migration()
        
        # 2. Insertar usuarios de prueba
        await insert_test_users()
        
        # 3. Actualizar productos para tienda online
        await update_products_for_online_store()
        
        # 4. Mostrar resumen
        await show_database_summary()
        
        print("\n" + "=" * 60)
        print("✅ PROCESO COMPLETADO EXITOSAMENTE")
        print("=" * 60)
        print("\n💡 Credenciales de prueba:")
        print("   Usuario: juan.perez")
        print("   Password: password123")
        print("\n   Usuario: maria.garcia")
        print("   Password: password123")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
