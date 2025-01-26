import base64
import google.generativeai as genai
from config import Config

def pdf2md(pdf_data: bytes, prompt="Turn this document into markdown") -> str:
    genai.configure(api_key=Config.GoogleAPIKey)
    pdf_enc = base64.standard_b64encode(pdf_data).decode("utf-8")

    model = genai.GenerativeModel("gemini-1.5-flash")
    response = model.generate_content([{'mime_type':'application/pdf', 'data': pdf_enc}, prompt])
    return response.text