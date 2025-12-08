"""
User authentication routes for web users.
Handles registration, login, logout, and user profile management.
Includes email verification infrastructure for EmailJS integration.
"""

from fastapi import APIRouter, HTTPException, Header, status
from typing import Optional
import bcrypt
import uuid
from datetime import datetime

from models.user_models import (
    UserRegister,
    UserLogin,
    UserResponse,
    TokenResponse,
    UserUpdate,
    PasswordChange,
    EmailVerification,
    ResendVerification
)
from config.db_connection import DatabaseManager

router = APIRouter()


# Helper functions
def hash_password(password: str) -> str:
    """Hash a password using bcrypt."""
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
    return hashed.decode('utf-8')


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash."""
    return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))


def generate_session_token() -> str:
    """Generate a unique session token."""
    return str(uuid.uuid4())


def generate_verification_token() -> str:
    """Generate a unique email verification token."""
    return str(uuid.uuid4())


async def get_user_by_token(token: str):
    """Get user by session token."""
    pool = await DatabaseManager.get_pool()
    async with pool.acquire() as conn:
        user = await conn.fetchrow(
            """
            SELECT id, username, fullname, email, phone, domicilio, cuit, 
                   role, status, profile_image_url, email_verified, google_id, created_at
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


# Endpoints
@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register(user_data: UserRegister):
    """
    Register a new web user.
    
    - **username**: Unique username (3-50 characters)
    - **email**: Valid email address
    - **password**: Password (minimum 6 characters)
    - **fullname**: Full name (optional)
    - **phone**: Phone number (optional)
    - **domicilio**: Address (optional)
    - **cuit**: CUIT (optional)
    
    After registration, user will receive a verification email.
    """
    pool = await DatabaseManager.get_pool()
    
    async with pool.acquire() as conn:
        # Check if username already exists
        existing_user = await conn.fetchrow(
            "SELECT id FROM web_users WHERE username = $1",
            user_data.username
        )
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Username already exists"
            )
        
        # Check if email already exists
        existing_email = await conn.fetchrow(
            "SELECT id FROM web_users WHERE email = $1",
            user_data.email
        )
        if existing_email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered"
            )
        
        # Hash password and generate tokens
        hashed_password = hash_password(user_data.password)
        session_token = generate_session_token()
        verification_token = generate_verification_token()
        
        # Insert new user
        new_user = await conn.fetchrow(
            """
            INSERT INTO web_users 
            (username, fullname, email, password, phone, domicilio, cuit, 
             role, status, session_token, email_verified, verification_token)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12)
            RETURNING id, username, fullname, email, phone, domicilio, cuit, 
                      role, status, profile_image_url, email_verified, google_id, created_at
            """,
            user_data.username,
            user_data.fullname,
            user_data.email,
            hashed_password,
            user_data.phone,
            user_data.domicilio,
            user_data.cuit,
            "customer",  # Default role
            "active",    # Default status
            session_token,
            False,       # email_verified
            verification_token
        )
        
        user_response = UserResponse(**dict(new_user))
        
        # TODO: Send verification email using EmailJS from frontend
        # The verification_token should be sent to the user's email
        # Frontend will handle this using EmailJS with the verification link:
        # http://yourfrontend.com/verify-email?token={verification_token}
        
        return TokenResponse(
            token=session_token,
            user=user_response,
            message="Registration successful. Please check your email to verify your account."
        )


@router.post("/verify-email")
async def verify_email(verification_data: EmailVerification):
    """
    Verify user email with verification token.
    
    - **token**: Verification token from email
    """
    pool = await DatabaseManager.get_pool()
    
    async with pool.acquire() as conn:
        # Find user by verification token
        user = await conn.fetchrow(
            "SELECT id, email_verified FROM web_users WHERE verification_token = $1",
            verification_data.token
        )
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid or expired verification token"
            )
        
        if user['email_verified']:
            return {"message": "Email already verified"}
        
        # Update user as verified
        await conn.execute(
            """
            UPDATE web_users 
            SET email_verified = TRUE, verification_token = NULL 
            WHERE id = $1
            """,
            user['id']
        )
    
    return {"message": "Email verified successfully"}


@router.post("/resend-verification")
async def resend_verification(resend_data: ResendVerification):
    """
    Resend verification email.
    
    - **email**: Email address to resend verification
    """
    pool = await DatabaseManager.get_pool()
    
    async with pool.acquire() as conn:
        # Find user by email
        user = await conn.fetchrow(
            "SELECT id, email_verified, verification_token FROM web_users WHERE email = $1",
            resend_data.email
        )
        
        if not user:
            # Don't reveal if email exists or not for security
            return {"message": "If the email exists, a verification link has been sent"}
        
        if user['email_verified']:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already verified"
            )
        
        # Generate new verification token if needed
        verification_token = user['verification_token'] or generate_verification_token()
        
        await conn.execute(
            "UPDATE web_users SET verification_token = $1 WHERE id = $2",
            verification_token,
            user['id']
        )
        
        # TODO: Send verification email using EmailJS from frontend
        # Frontend should call this endpoint and then send the email
        # with the verification link containing the token
    
    return {"message": "If the email exists, a verification link has been sent"}


@router.post("/login", response_model=TokenResponse)
async def login(credentials: UserLogin):
    """
    Login with username/email and password.
    
    - **username**: Username or email
    - **password**: User password
    
    Note: Email must be verified to login (can be disabled for development).
    """
    pool = await DatabaseManager.get_pool()
    
    async with pool.acquire() as conn:
        # Try to find user by username or email
        user = await conn.fetchrow(
            """
            SELECT id, username, fullname, email, phone, domicilio, cuit, 
                   role, status, profile_image_url, email_verified, google_id, created_at, password
            FROM web_users
            WHERE (username = $1 OR email = $1)
            """,
            credentials.username
        )
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid username or password"
            )
        
        # Verify password
        if not verify_password(credentials.password, user['password']):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid username or password"
            )
        
        # Check if user is active
        if user['status'] != 'active':
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User account is not active"
            )
        
        # TODO: Uncomment this when email verification is fully implemented
        # Check if email is verified
        # if not user['email_verified']:
        #     raise HTTPException(
        #         status_code=status.HTTP_403_FORBIDDEN,
        #         detail="Please verify your email before logging in"
        #     )
        
        # Generate new session token
        session_token = generate_session_token()
        
        # Update session token in database
        await conn.execute(
            "UPDATE web_users SET session_token = $1 WHERE id = $2",
            session_token,
            user['id']
        )
        
        # Remove password from user data
        user_dict = dict(user)
        user_dict.pop('password')
        user_response = UserResponse(**user_dict)
        
        return TokenResponse(
            token=session_token,
            user=user_response,
            message="Login successful"
        )


@router.post("/logout")
async def logout(authorization: Optional[str] = Header(None)):
    """
    Logout and invalidate session token.
    
    Requires Authorization header with Bearer token.
    """
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid authorization header"
        )
    
    token = authorization.replace("Bearer ", "")
    pool = await DatabaseManager.get_pool()
    
    async with pool.acquire() as conn:
        # Clear session token
        result = await conn.execute(
            "UPDATE web_users SET session_token = NULL WHERE session_token = $1",
            token
        )
        
        if result == "UPDATE 0":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token"
            )
    
    return {"message": "Logout successful"}


@router.get("/me", response_model=UserResponse)
async def get_current_user(authorization: Optional[str] = Header(None)):
    """
    Get current authenticated user information.
    
    Requires Authorization header with Bearer token.
    """
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid authorization header"
        )
    
    token = authorization.replace("Bearer ", "")
    user = await get_user_by_token(token)
    
    return UserResponse(**user)


@router.put("/me", response_model=UserResponse)
async def update_current_user(
    user_update: UserUpdate,
    authorization: Optional[str] = Header(None)
):
    """
    Update current user information.
    
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
    
    # Build update query dynamically based on provided fields
    update_fields = []
    values = []
    param_count = 1
    
    if user_update.fullname is not None:
        update_fields.append(f"fullname = ${param_count}")
        values.append(user_update.fullname)
        param_count += 1
    
    if user_update.email is not None:
        # Check if email is already used by another user
        async with pool.acquire() as conn:
            existing = await conn.fetchrow(
                "SELECT id FROM web_users WHERE email = $1 AND id != $2",
                user_update.email,
                current_user['id']
            )
            if existing:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Email already in use"
                )
        
        update_fields.append(f"email = ${param_count}")
        values.append(user_update.email)
        param_count += 1
    
    if user_update.phone is not None:
        update_fields.append(f"phone = ${param_count}")
        values.append(user_update.phone)
        param_count += 1
    
    if user_update.domicilio is not None:
        update_fields.append(f"domicilio = ${param_count}")
        values.append(user_update.domicilio)
        param_count += 1
    
    if user_update.profile_image_url is not None:
        update_fields.append(f"profile_image_url = ${param_count}")
        values.append(user_update.profile_image_url)
        param_count += 1
    
    if not update_fields:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No fields to update"
        )
    
    # Add user ID as last parameter
    values.append(current_user['id'])
    
    query = f"""
        UPDATE web_users 
        SET {', '.join(update_fields)}
        WHERE id = ${param_count}
        RETURNING id, username, fullname, email, phone, domicilio, cuit, 
                  role, status, profile_image_url, email_verified, google_id, created_at
    """
    
    async with pool.acquire() as conn:
        updated_user = await conn.fetchrow(query, *values)
    
    return UserResponse(**dict(updated_user))


@router.post("/change-password")
async def change_password(
    password_data: PasswordChange,
    authorization: Optional[str] = Header(None)
):
    """
    Change user password.
    
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
        # Get current password hash
        user = await conn.fetchrow(
            "SELECT password FROM web_users WHERE id = $1",
            current_user['id']
        )
        
        # Verify current password
        if not verify_password(password_data.current_password, user['password']):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Current password is incorrect"
            )
        
        # Hash new password
        new_hashed_password = hash_password(password_data.new_password)
        
        # Update password
        await conn.execute(
            "UPDATE web_users SET password = $1 WHERE id = $2",
            new_hashed_password,
            current_user['id']
        )
    
    return {"message": "Password changed successfully"}


# TODO: Google OAuth endpoint - Implement when Google OAuth is configured
# @router.post("/auth/google")
# async def google_auth(google_token: str):
#     """
#     Authenticate with Google OAuth.
#     
#     This endpoint will:
#     1. Verify the Google token
#     2. Extract user information (email, name, google_id)
#     3. Create user if doesn't exist or login if exists
#     4. Return session token
#     
#     See GOOGLE_OAUTH_SETUP.md for configuration instructions.
#     """
#     pass
