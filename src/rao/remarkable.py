import json
import re
import stat
import tempfile
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import datetime
from hashlib import sha256
from io import BytesIO
from pathlib import Path

import pandas as pd
import paramiko
from loguru import logger
from paramiko import SFTPClient
from pypdf import PageObject, PdfReader, PdfWriter
from remarks.remarks import process_document

from .config import Config
from .models import RemarkableFile, RemarkablePage

FILES_ROOT = Path("/home/root/.local/share/remarkable/xochitl/")
TEMPLATES_ROOT = Path("/usr/share/remarkable/templates/")
SVG_VIEWBOX_PATTERN = re.compile(
    r"^<svg .+ viewBox=\"([\-\d.]+) ([\-\d.]+) ([\-\d.]+) ([\-\d.]+)\">$"
)
TEMPLATE_CACHE_DIR = Path("./data/templates_cache")
RENDER_TEMPLATES = False  # Currently not properly supported in RMC


@contextmanager
def connect(retries: int = 5) -> Iterator[paramiko.SSHClient | None]:
    pk_file = Path(Config.ssh_key_path)
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
                Config.remarkable_ip_address, username="root", pkey=pkey, timeout=5
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
    files = _load_metadata_files(sftp, files_df)
    files = [
        file
        for file in files
        if file.type == "DocumentType" and file.parent_uuid != "trash"
    ]
    sftp.close()
    return files


def _load_metadata_files(
    sftp: paramiko.SSHClient, files_df: pd.DataFrame
) -> RemarkableFile:
    meta_files = files_df[files_df.filename.str.endswith(".metadata")]

    meta_file_contents = {}
    for _, row in meta_files.iterrows():
        meta_filename = row.filename
        uuid = Path(meta_filename).stem
        if uuid in meta_file_contents:
            logger.warning(f"Duplicate entry for metadata file {uuid}")
            continue
        other_files = files_df[
            files_df.filename.str.contains(uuid)
            & (files_df.filename.str.contains("."))
            & (~files_df.filename.str.contains(".metadata"))
            & (~files_df.filename.str.contains(".thumbnails"))
        ].filename.to_list()
        meta_content = json.loads(sftp.open(str(FILES_ROOT / meta_filename)).read())
        meta_file_contents[uuid] = {
            **meta_content,
            "st_mtime": row.st_mtime,
            "other_files": other_files,
        }
    paths = _load_file_paths(meta_file_contents)

    return [
        RemarkableFile(
            uuid=uuid,
            last_modified=datetime.fromtimestamp(meta["st_mtime"]),
            parent_uuid=meta["parent"],
            name=meta["visibleName"],
            type=meta["type"],
            path=paths[uuid],
            other_files=meta["other_files"],
        )
        for uuid, meta in meta_file_contents.items()
    ]


def _load_file_paths(
    files: dict[str, dict],
) -> dict[str, Path]:
    paths = {}
    for uuid, meta in files.items():
        path = [meta["visibleName"]]
        parent_uuid = meta["parent"]
        parent = files.get(parent_uuid)
        while parent:
            path.append(parent["visibleName"])
            parent = files.get(parent["parent"])
        paths[uuid] = Path("/".join(reversed(path)))
    return paths


def render_pages(
    client: paramiko.SSHClient, metadata_file: RemarkableFile
) -> list[RemarkablePage]:
    TEMPLATE_CACHE_DIR.mkdir(exist_ok=True, parents=True)
    sftp = client.open_sftp()
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        files_dir = tmpdir / "files"
        files_dir.mkdir()
        files = _download_files(metadata_file, sftp, files_dir)
        content_file = _load_content_file(
            files.get(f"{metadata_file.uuid}.content", None)
        )
        if not content_file:
            logger.info(f"No content file for {metadata_file.uuid}")
            sftp.close()
            return []
        pages, templates_per_page = _load_pages_and_templates(content_file)
        if RENDER_TEMPLATES:
            templates_per_page = _download_templates(templates_per_page, sftp)
        else:
            templates_per_page = None
        output_path = tmpdir / "rendered"
        process_document(
            metadata_path=files[f"{metadata_file.uuid}.metadata"],
            out_path=output_path,
            templates_per_page=templates_per_page,
        )
        pdf = PdfReader(output_path.with_name(output_path.stem + " _remarks.pdf"))
    sftp.close()

    pdf_bytes = [_pdf_page_to_bytes(page) for page in pdf.pages]
    return [
        RemarkablePage(
            page_idx=i,
            parent=metadata_file,
            uuid=page["id"],
            pdf_data=page_data,
            hash=sha256(page_data).hexdigest(),
        )
        for i, (page_data, page) in enumerate(zip(pdf_bytes, pages))
    ]


def _download_files(
    metadata_file: RemarkableFile, sftp: SFTPClient, output_dir: Path
) -> dict:
    paths_to_copy = [str(FILES_ROOT / file) for file in metadata_file.other_files] + [
        str(FILES_ROOT / f"{metadata_file.uuid}.metadata")
    ]
    file_paths = {}
    while paths_to_copy:
        remote_path = paths_to_copy.pop(0)
        if stat.S_ISDIR(sftp.stat(remote_path).st_mode):
            paths_to_copy += [
                str(Path(remote_path) / path) for path in sftp.listdir(remote_path)
            ]
        else:
            target_path = output_dir / Path(remote_path).relative_to(FILES_ROOT)
            target_path.parent.mkdir(exist_ok=True, parents=True)
            sftp.get(remote_path, str(target_path))
            file_paths[target_path.name] = target_path
    return file_paths


def _download_templates(
    templates_per_page: dict[str, str], sftp: SFTPClient
) -> dict[str, Path]:
    downloaded = {}
    for page, template in templates_per_page.items():
        target_path = TEMPLATE_CACHE_DIR / (template + ".svg")
        if not target_path.exists():
            sftp.get(str(TEMPLATES_ROOT / target_path.name), str(target_path))
        downloaded[page] = target_path
    return downloaded


def _load_content_file(content_file_path: Path | None) -> dict:
    if content_file_path is None:
        return {}
    return json.loads(content_file_path.read_text())


def _load_pages_and_templates(content_file: dict) -> tuple[dict, dict]:
    if "cPages" in content_file:
        pages = content_file.get("cPages", {}).get("pages", [])
    else:
        pages = [{"id": page} for page in content_file["pages"]]
    templates_per_page = {
        page["id"]: page.get("template", {}).get("value", "Blank") for page in pages
    }
    templates_per_page = {
        page_id: template
        for page_id, template in templates_per_page.items()
        if template != "Blank"
    }
    return pages, templates_per_page


def _pdf_page_to_bytes(page: PageObject) -> bytes:
    writer = PdfWriter()
    with BytesIO() as bytes_stream:
        writer.add_page(page)
        writer.write(bytes_stream)
        return bytes_stream.getvalue()
