"""
Contact form routes
Handles contact form submissions from the website
"""

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, EmailStr
from typing import Optional

from utils.email import send_contact_email

router = APIRouter()


class ContactForm(BaseModel):
    name: str
    email: EmailStr
    phone: Optional[str] = None
    message: str


@router.post("/submit")
async def submit_contact_form(form_data: ContactForm):
    """
    Submit contact form
    
    - **name**: Sender's name
    - **email**: Sender's email
    - **phone**: Sender's phone (optional)
    - **message**: Message content
    """
    try:
        await send_contact_email(
            name=form_data.name,
            email=form_data.email,
            phone=form_data.phone or "",
            message_text=form_data.message
        )
        
        return {
            "success": True,
            "message": "Message sent successfully"
        }
    except Exception as e:
        print(f"Error sending contact email: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to send message. Please try again later."
        )
