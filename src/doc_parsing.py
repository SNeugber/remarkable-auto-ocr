import base64
from file_processing_config import ProcessingConfig
import google.generativeai as genai
from config import Config
from loguru import logger
from models import RemarkableFile, RemarkablePage


def pages_to_md(
    pages: list[RemarkablePage], file_configs: dict[RemarkableFile, ProcessingConfig]
) -> dict[RemarkablePage, str]:
    rendered = {}
    failed: list[RemarkablePage] = []
    for page in pages:
        if file_configs[page.parent].pdf_only:
            rendered[page] = None
            continue
        md = _pdf2md(page.pdf_data, prompt=file_configs[page.parent].prompt)
        if md:
            rendered[page] = md
        else:
            failed.append(page)
    for page in failed:
        logger.error(
            f"Failed to convert {page.page_idx} of file {page.parent.name} to markdown."
        )
    return rendered


def _pdf2md(pdf_data: bytes, prompt: str) -> str:
    genai.configure(api_key=Config.google_api_key)
    pdf_enc = base64.standard_b64encode(pdf_data).decode("utf-8")

    model = genai.GenerativeModel("gemini-1.5-flash")
    try:
        response = model.generate_content(
            [{"mime_type": "application/pdf", "data": pdf_enc}, prompt]
        )
        return response.text
    except Exception as e:
        logger.error(f"Failed to convert PDF to markdown.\n{e}")
        return None
