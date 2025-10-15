import io
from PIL import Image
import pytesseract
from typing import List
import fitz 

# Ensure Tesseract-OCR is installed on your system and its path is correctly set if not in PATH.
# For example, on macOS: brew install tesseract
# On Debian/Ubuntu: sudo apt install tesseract-ocr
# For Windows, download from: https://tesseract-ocr.github.io/tessdoc/Downloads.html
# You might need to set pytesseract.pytesseract.tesseract_cmd = r'<full_path_to_tesseract_executable>'

async def extract_text_from_image(image_bytes: bytes) -> str:
    """
    Extracts text from an image using OCR.
    """
    try:
        image = Image.open(io.BytesIO(image_bytes))
        text = pytesseract.image_to_string(image)
        return text
    except Exception as e:
        print(f"Error extracting text from image: {e}")
        return ""

async def extract_text_from_pdf(pdf_bytes: bytes) -> List[str]:
    """
    Extracts text from each page of a PDF using OCR.
    Returns a list of strings, where each string is the text from a page.
    """
    extracted_texts = []
    try:
        # Open the PDF from bytes
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        for page_num in range(doc.page_count):
            page = doc.load_page(page_num)
            # Render page to an image (pixmap)
            pix = page.get_pixmap()
            img_bytes = pix.tobytes("png")
            
            # Use the image OCR function for each page
            page_text = await extract_text_from_image(img_bytes)
            extracted_texts.append(page_text)
        doc.close()
        return extracted_texts
    except Exception as e:
        print(f"Error extracting text from PDF: {e}")
        return []

async def extract_text_from_file(file_bytes: bytes, file_type: str) -> str:
    """
    Extracts text from a given file (image or PDF) based on its type.
    """
    if file_type.startswith("image/"):
        return await extract_text_from_image(file_bytes)
    elif file_type == "application/pdf":
        # For PDF, we'll join the text from all pages for a single preview string
        page_texts = await extract_text_from_pdf(file_bytes)
        return "\n\n".join(page_texts)
    else:
        raise ValueError("Unsupported file type for OCR.")
