from google import genai
from google.genai import types
from loguru import logger
from pydantic import BaseModel

from .config import Config
from .file_processing_config import ProcessingConfig
from .models import RemarkableFile, RemarkablePage


class MDContentSchema(BaseModel):
    markdown: str


def pages_to_md(
    pages: list[RemarkablePage], file_configs: dict[RemarkableFile, ProcessingConfig]
) -> tuple[dict[RemarkablePage, str], set[RemarkablePage]]:
    logger.info(f"Converting {len(pages)} to markdown")
    rendered = {}
    failed: set[RemarkablePage] = set()
    for page in pages:
        if file_configs[page.parent].pdf_only:
            continue
        md = _pdf2md(page.pdf_data, prompt=file_configs[page.parent].prompt)
        if md:
            rendered[page] = md
        else:
            failed.add(page)
    for page in failed:
        logger.error(
            f"Failed to convert page {page.page_idx} of file {page.parent.name} to markdown."
        )
    logger.info(
        f"Converted {len(rendered)} to markdown, failed to convert {len(failed)}"
    )
    return rendered, failed


def _pdf2md(pdf_data: bytes, prompt: str) -> str:
    # genai.configure(api_key=Config.google_api_key)
    client = genai.Client(api_key=Config.google_api_key)

    exception = None
    for model_name in [Config.model, Config.backup_model]:
        # model = genai.GenerativeModel(model_name)
        try:
            response = client.models.generate_content(
                model=model_name,
                contents=[prompt, types.Part.from_bytes(pdf_data, "application/pdf")],
                config={
                    "response_mime_type": "application/json",
                    "response_schema": MDContentSchema,
                },
            )
            mdcontent: MDContentSchema = response.parsed
            return mdcontent.markdown
        except Exception as e:
            logger.warning(
                f"Failed to get response using model {model_name}. Trying backup..."
            )
            exception = e
    logger.error(f"Failed to convert PDF to markdown.\n{exception}")
    return None
