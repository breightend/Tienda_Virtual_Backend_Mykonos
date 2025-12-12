#!/usr/bin/env python3
"""
Script to create an admin user for Mykonos backend.
Creates user: tapari.brenda with admin privileges.
"""

import asyncio
import asyncpg
import bcrypt
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Database configuration
DB_CONFIG = {
    "host": os.getenv("DB_HOST", "localhost"),
    "port": int(os.getenv("DB_PORT", "5432")),
    "database": os.getenv("DB_NAME", "mykonos_db"),
    "user": os.getenv("DB_USER", "postgres"),
    "password": os.getenv("DB_PASSWORD"),
}


def hash_password(password: str) -> str:
    """Hash a password using bcrypt."""
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
    return hashed.decode('utf-8')


async def create_admin_user():
    """Create the admin user in the database."""
    print("🔧 Conectando a la base de datos...")
    
    try:
        conn = await asyncpg.connect(**DB_CONFIG)
        
        # Check if user already exists
        existing = await conn.fetchrow(
            "SELECT id, username, role FROM web_users WHERE username = $1",
            "tapari.brenda"
        )
        
        if existing:
            print(f"⚠️  El usuario 'tapari.brenda' ya existe (ID: {existing['id']}, Role: {existing['role']})")
            
            # Update to admin if not already
            if existing['role'] != 'admin':
                await conn.execute(
                    "UPDATE web_users SET role = 'admin' WHERE id = $1",
                    existing['id']
                )
                print("✅ Usuario actualizado a role 'admin'")
            else:
                print("✅ El usuario ya tiene role 'admin'")
            
            await conn.close()
            return
        
        # Hash the password
        hashed_password = hash_password("Michifus1107")
        
        print("📝 Creando usuario admin...")
        
        # Create the admin user
        new_user = await conn.fetchrow(
            """
            INSERT INTO web_users 
            (username, fullname, email, password, role, status, email_verified)
            VALUES ($1, $2, $3, $4, $5, $6, $7)
            RETURNING id, username, fullname, email, role, status
            """,
            "tapari.brenda",
            "Brenda Tapari",
            "tapari.brenda@mykonos.com",
            hashed_password,
            "admin",
            "active",
            True  # Skip email verification for admin
        )
        
        print("✅ Usuario admin creado exitosamente!")
        print(f"\n📋 Detalles del usuario:")
        print(f"   ID: {new_user['id']}")
        print(f"   Username: {new_user['username']}")
        print(f"   Fullname: {new_user['fullname']}")
        print(f"   Email: {new_user['email']}")
        print(f"   Role: {new_user['role']}")
        print(f"   Status: {new_user['status']}")
        print(f"\n🔑 Credenciales:")
        print(f"   Username: tapari.brenda")
        print(f"   Password: Michifus1107")
        
        await conn.close()
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return False


if __name__ == "__main__":
    asyncio.run(create_admin_user())
