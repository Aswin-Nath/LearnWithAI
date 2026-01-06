"""Utility for uploading and deleting PDFs from Cloudinary"""
from app.core.cloudinary_config import uploader


async def upload_pdf_to_cloudinary(file_bytes: bytes, filename: str) -> dict:
    """
    Upload a PDF file to Cloudinary
    
    Args:
        file_bytes: PDF file content as bytes
        filename: Original filename (used as reference)
    
    Returns:
        dict with 'url' and 'public_id'
    """
    upload_res = uploader.upload(
        file_bytes,
        folder="ticket_raiser/editorials",
        resource_type="raw",  # PDF is treated as raw resource
        format="pdf"
    )
    return {
        "url": upload_res["secure_url"],
        "public_id": upload_res["public_id"]
    }


def delete_pdf_from_cloudinary(public_id: str) -> bool:
    """
    Delete a PDF file from Cloudinary
    
    Args:
        public_id: Public ID of the file in Cloudinary (e.g., 'ticket_raiser/editorials/filename')
    
    Returns:
        bool: True if deletion was successful
    """
    try:
        result = uploader.destroy(public_id, resource_type="raw")
        return result.get("result") == "ok"
    except Exception as e:
        raise Exception(f"Failed to delete PDF from Cloudinary: {str(e)}")

