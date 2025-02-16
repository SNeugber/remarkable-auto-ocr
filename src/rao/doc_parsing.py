import google.api_core.exceptions as google_exceptions
from backoff import expo, on_exception
from google import genai
from google.genai import errors as genai_errors
from google.genai import types
from loguru import logger
from pydantic import BaseModel
from ratelimit import limits, sleep_and_retry
from tqdm import tqdm

from .config import Config
from .file_processing_config import ProcessingConfig
from .models import RemarkableFile, RemarkablePage


class MDContentSchema(BaseModel):
    markdown: str


def pages_to_md(
    pages: list[RemarkablePage], file_configs: dict[RemarkableFile, ProcessingConfig]
) -> tuple[dict[RemarkablePage, str], set[RemarkablePage]]:
    rendered = {}
    failed: set[RemarkablePage] = set()
    for page in tqdm(pages, f"Converting {len(pages)} to markdown"):
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


@sleep_and_retry
@on_exception(expo, google_exceptions.ResourceExhausted, max_tries=3)
@limits(calls=60, period=60)
def _call_api_rate_limited(
    client: genai.Client, model_name: str, prompt: str, pdf_data: bytes
):
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
    except genai_errors.ClientError as e:
        if e.code == 429 or e.status == "RESOURCE_EXHAUSTED":
            raise google_exceptions.ResourceExhausted(e.message) from e
        raise e


def _pdf2md(pdf_data: bytes, prompt: str) -> str:
    client = genai.Client(api_key=Config.google_api_key)
    exception = None
    for model_name in [Config.model, Config.backup_model]:
        try:
            return _call_api_rate_limited(client, model_name, prompt, pdf_data)
        except Exception as e:
            logger.warning(
                f"Failed to get response using model {model_name}.\n{e}\n Trying backup..."
            )
            exception = e
    logger.error(f"Failed to convert PDF to markdown.\n{exception}")
    return None
