#!/usr/bin/env python3
"""
Script de migración de base de datos para Mykonos
Ejecuta las migraciones SQL y verifica la conexión a PostgreSQL
"""

import asyncio
import asyncpg
import os
from dotenv import load_dotenv
from pathlib import Path

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


async def test_connection():
    """Prueba la conexión a la base de datos"""
    print("🔍 Verificando conexión a la base de datos...")
    print(f"   Host: {DB_CONFIG['host']}")
    print(f"   Puerto: {DB_CONFIG['port']}")
    print(f"   Base de datos: {DB_CONFIG['database']}")
    print(f"   Usuario: {DB_CONFIG['user']}")
    
    try:
        conn = await asyncpg.connect(**DB_CONFIG)
        version = await conn.fetchval("SELECT version()")
        print(f"✅ Conexión exitosa!")
        print(f"   PostgreSQL: {version.split(',')[0]}")
        await conn.close()
        return True
    except Exception as e:
        print(f"❌ Error de conexión: {e}")
        return False


async def run_migration(migration_file: Path):
    """Ejecuta un archivo de migración SQL"""
    print(f"\n📄 Ejecutando migración: {migration_file.name}")
    
    # Leer el archivo SQL
    with open(migration_file, 'r', encoding='utf-8') as f:
        sql_content = f.read()
    
    try:
        conn = await asyncpg.connect(**DB_CONFIG)
        
        # Ejecutar la migración dentro de una transacción
        print("⚙️  Ejecutando SQL...")
        await conn.execute(sql_content)
        
        print("✅ Migración ejecutada exitosamente!")
        await conn.close()
        return True
        
    except Exception as e:
        print(f"❌ Error ejecutando migración: {e}")
        return False


async def verify_tables():
    """Verifica que las nuevas tablas se hayan creado"""
    print("\n🔍 Verificando tablas creadas...")
    
    expected_tables = [
        'web_users',
        'web_carts',
        'web_cart_items',
        'sales_tracking_history'
    ]
    
    try:
        conn = await asyncpg.connect(**DB_CONFIG)
        
        for table in expected_tables:
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
            
            if exists:
                # Contar registros
                count = await conn.fetchval(f"SELECT COUNT(*) FROM {table}")
                print(f"   ✅ {table} - {count} registros")
            else:
                print(f"   ❌ {table} - NO EXISTE")
        
        # Verificar nuevas columnas en products
        print("\n🔍 Verificando columnas nuevas en 'products'...")
        new_columns = ['en_tienda_online', 'nombre_web', 'descripcion_web', 'slug']
        
        for column in new_columns:
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
            print(f"   {status} products.{column}")
        
        # Verificar nuevas columnas en sales
        print("\n🔍 Verificando columnas nuevas en 'sales'...")
        sales_columns = ['origin', 'shipping_address', 'shipping_status', 
                        'external_payment_id', 'shipping_cost', 'web_user_id', 'delivery_type']
        
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
            print(f"   {status} sales.{column}")
        
        await conn.close()
        
    except Exception as e:
        print(f"❌ Error verificando tablas: {e}")


async def main():
    """Función principal"""
    print("=" * 60)
    print("🚀 MIGRACIÓN DE BASE DE DATOS - MYKONOS")
    print("=" * 60)
    
    # 1. Verificar conexión
    if not await test_connection():
        print("\n❌ No se pudo conectar a la base de datos.")
        print("   Verifica las credenciales en el archivo .env")
        return
    
    # 2. Ejecutar migración
    migration_file = Path(__file__).parent / "migrations" / "001_tienda_online.sql"
    
    if not migration_file.exists():
        print(f"\n❌ No se encontró el archivo de migración: {migration_file}")
        return
    
    print("\n" + "=" * 60)
    response = input("¿Deseas ejecutar la migración? (s/n): ")
    
    if response.lower() != 's':
        print("❌ Migración cancelada por el usuario")
        return
    
    success = await run_migration(migration_file)
    
    if not success:
        print("\n❌ La migración falló. Revisa los errores anteriores.")
        return
    
    # 3. Verificar tablas
    await verify_tables()
    
    print("\n" + "=" * 60)
    print("✅ PROCESO COMPLETADO")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
