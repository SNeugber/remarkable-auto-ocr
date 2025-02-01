from datetime import datetime
import json
from pathlib import Path
import tempfile
from loguru import logger
import pandas as pd
from rmc import rm_to_pdf
from pypdf import PdfWriter

import paramiko
from models import RemarkableFile, RemarkablePage
from config import Config
from contextlib import contextmanager
from collections.abc import Iterator
from hashlib import sha256

FILES_ROOT = Path("/home/root/.local/share/remarkable/xochitl/")


@contextmanager
def connect(retries: int = 5) -> Iterator[paramiko.SSHClient | None]:
    pk_file = Path(Config.SSHKeyPath)
    if not pk_file.exists():
        raise FileNotFoundError(pk_file)
    loader = (
        paramiko.Ed25519Key if "ed25519" in pk_file.stem.lower() else paramiko.RSAKey
    )
    pkey = loader.from_private_key_file(pk_file)
    client = paramiko.SSHClient()
    policy = paramiko.AutoAddPolicy()
    client.set_missing_host_key_policy(policy)
    connected = False
    for _ in range(retries):
        try:
            client.connect(
                Config.RemarkableIPAddress, username="root", pkey=pkey, timeout=5
            )
            connected = True
            break
        except TimeoutError:
            continue

    try:
        yield client if connected else None
    finally:
        client.close()


def get_files(
    client: paramiko.SSHClient,
) -> list[RemarkableFile]:
    sftp = client.open_sftp()
    files_df = pd.DataFrame(
        [attr.__dict__ for attr in sftp.listdir_attr(str(FILES_ROOT))]
    )
    meta_files = files_df[files_df.filename.str.endswith(".metadata")]
    files = list(
        meta_files.apply(
            lambda file: load_metadata_file(
                sftp, FILES_ROOT / file.filename, file.st_mtime
            ),
            axis=1,
        )
    )
    sftp.close()
    return files


def load_metadata_file(
    sftp: paramiko.SSHClient, metadata_file: Path, last_modified: int
) -> RemarkableFile:
    if metadata_file.suffix != ".metadata":
        raise ValueError("Use this function to load '.metadata' files")
    meta = json.loads(sftp.open(str(metadata_file)).read())
    return RemarkableFile(
        uuid=metadata_file.stem,
        last_modified=datetime.fromtimestamp(last_modified),
        parent_uuid=meta["parent"],
        name=meta["visibleName"],
        type=meta["type"],
    )


def render_pages(
    client: paramiko.SSHClient, metadata_file: RemarkableFile
) -> list[RemarkablePage]:
    sftp = client.open_sftp()
    try:
        content_file = FILES_ROOT / (metadata_file.uuid + ".content")
        content = json.loads(sftp.open(str(content_file)).read())
    except IOError as e:
        logger.info(f"No content file for {metadata_file.uuid}.\n{e}")
        sftp.close()
        return []

    pages = content.get("cPages", {}).get("pages", [])
    page_paths = [
        FILES_ROOT / metadata_file.uuid / f"{page['id']}.rm" for page in pages
    ]

    page_data = []
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        for i, page_path in enumerate(page_paths):
            try:
                sftp.get(str(page_path), str(tmpdir / page_path.name))
            except FileNotFoundError:
                logger.warning(f"Page does not exist {page_path}.")
                continue
            pdf_path = tmpdir / page_path.with_suffix(".pdf").name
            rm_to_pdf(tmpdir / page_path.name, pdf_path)
            with open(pdf_path, "rb") as f:
                data = f.read()
                page_data.append(
                    RemarkablePage(
                        page_idx=i,
                        parent_uuid=metadata_file.uuid,
                        uuid=page_path.stem,
                        data=data,
                        hash=sha256(data).hexdigest(),
                    )
                )
    sftp.close()
    return page_data


def merge_pdfs(pages: list[RemarkablePage]) -> bytes:
    writer = PdfWriter()
    for page in pages:
        writer.append(page.data)
    with tempfile.TemporaryDirectory() as tmpdir:
        pdf_path = Path(tmpdir) / "result.pdf"
        writer.write(pdf_path)
        writer.close()
        with open(pdf_path, "rb") as f:
            return f.read()
