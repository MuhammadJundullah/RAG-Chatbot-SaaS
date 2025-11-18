import os
import uuid
import pathlib
import logging
from fastapi import UploadFile

async def save_uploaded_file(file: UploadFile, upload_dir: str) -> str:
    """
    Saves an uploaded file to the specified directory and returns its relative URL path.
    """
    if not file.filename:
        raise ValueError("No file name provided.")

    # Ensure the upload directory exists
    pathlib.Path(upload_dir).mkdir(parents=True, exist_ok=True)

    # Generate a unique filename
    file_extension = os.path.splitext(file.filename)[1]
    file_uuid = str(uuid.uuid4())
    filename = f"{file_uuid}{file_extension}"
    file_path = os.path.join(upload_dir, filename)

    try:
        file_content = await file.read()
        with open(file_path, "wb") as f:
            f.write(file_content)
        
        # Return the URL path (e.g., /static/employee_profiles/filename.ext)
        return f"/{file_path}"
    except Exception as e:
        logging.error(f"Failed to save uploaded file {file.filename} to {file_path}: {e}")
        raise

def delete_static_file(file_url: str):
    """
    Deletes a static file from the filesystem given its URL path.
    """
    if not file_url:
        return

    # Convert URL path (e.g., /static/...) to local filesystem path
    # Remove leading '/' if present
    local_file_path = file_url.lstrip('/') 

    if os.path.exists(local_file_path):
        try:
            os.remove(local_file_path)
            logging.info(f"Deleted static file: {local_file_path}")
        except OSError as e:
            logging.error(f"Failed to delete static file {local_file_path}: {e}")
            # Decide whether to raise an error or just log it.
            # For now, we'll log and allow the process to continue.
