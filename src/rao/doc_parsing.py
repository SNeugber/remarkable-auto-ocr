import base64

import google.generativeai as genai
from loguru import logger

from .config import Config
from .file_processing_config import ProcessingConfig
from .models import RemarkableFile, RemarkablePage

DOC_FORMATTING_PROMPT = """
Ensure that the rendered document is wrapped in a markdown code block.
For example, given some document content denoted with the placeholder "<content>", it should look like:

```markdown

<content>

```
"""


def pages_to_md(
    pages: list[RemarkablePage], file_configs: dict[RemarkableFile, ProcessingConfig]
) -> tuple[dict[RemarkablePage, str], set[RemarkablePage]]:
    rendered = {}
    failed: set[RemarkablePage] = set()
    for page in pages:
        if file_configs[page.parent].pdf_only:
            continue
        md = _pdf2md(page.pdf_data, prompt=file_configs[page.parent].prompt)
        if md:
            rendered[page] = _postprocess(md, page)
        else:
            failed.add(page)
    for page in failed:
        logger.error(
            f"Failed to convert page {page.page_idx} of file {page.parent.name} to markdown."
        )
    return rendered, failed


def _postprocess(md: str, page: RemarkablePage) -> str:
    md = md.strip("\n")
    doc_start_idx = md.find("```markdown")
    if doc_start_idx >= 0:
        md = md[doc_start_idx + len("```markdown") :]
    elif md.startswith("```"):
        md = md[len("```") :]
    if md.endswith("```"):  # It doesn't always, thanks to GenAI randomness...
        md = md[: -len("```")]
    if doc_start_idx == -1:
        logger.warning(
            f"Malformed content for page {page.page_idx} of file {page.parent.name}. Returning as-is"
        )
    return md.strip("\n")


def _pdf2md(pdf_data: bytes, prompt: str) -> str:
    genai.configure(api_key=Config.google_api_key)
    pdf_enc = base64.standard_b64encode(pdf_data).decode("utf-8")
    prompt = prompt + DOC_FORMATTING_PROMPT

    exception = None
    for model in [Config.model, Config.backup_model]:
        model = genai.GenerativeModel(model)
        try:
            response = model.generate_content(
                [{"mime_type": "application/pdf", "data": pdf_enc}, prompt]
            )
            return response.text
        except Exception as e:
            exception = e
    logger.error(f"Failed to convert PDF to markdown.\n{exception}")
    return None
