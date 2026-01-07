import requests
import io
import pdfplumber
from pypdf import PdfReader
import warnings

# Suppress pdfplumber font warnings globally (common with malformed PDFs)
warnings.filterwarnings('ignore', message='.*FontBBox.*')

def download_pdf(url: str) -> bytes:
    response = requests.get(url)
    response.raise_for_status()
    return response.content

def extract_text_from_pdf(pdf_content: bytes) -> str:
    # Suppress pdfplumber font warnings (common with malformed PDFs)
    warnings.filterwarnings('ignore', message='.*FontBBox.*')
    text = ""
    # 1. Try pdfplumber (Better for layout/columns)
    try:
        with pdfplumber.open(io.BytesIO(pdf_content)) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n"
    except Exception as e:
        print(f"pdfplumber failed: {e}")

    # 2. Fallback to pypdf if text is suspiciously short or empty
    if len(text.strip()) < 50:
        print("Falling back to pypdf...")
        try:
            reader = PdfReader(io.BytesIO(pdf_content))
            pypdf_text = ""
            for page in reader.pages:
                pypdf_text += page.extract_text() + "\n"
            
            # Use pypdf text if it managed to extract more
            if len(pypdf_text) > len(text):
                text = pypdf_text
        except Exception as e:
            print(f"pypdf failed: {e}")
            
    return text
