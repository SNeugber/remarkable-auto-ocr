from collections import namedtuple
from datetime import datetime
import json
from pathlib import Path
import tempfile
from loguru import logger
import pandas as pd
from rmc import rm_to_pdf

import paramiko
from models import RemarkableFile, RemarkablePage
from config import Config
from contextlib import contextmanager
from collections.abc import Iterator
from hashlib import sha256

FILES_ROOT = Path("/home/root/.local/share/remarkable/xochitl/")
TmpMetadata = namedtuple("Metadata", ["filename", "st_mtime"])


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
    meta_files = files_df[files_df.filename.str.endswith(".metadata")]
    meta_files = [
        TmpMetadata(*row) for row in meta_files[["filename", "st_mtime"]].values
    ]
    files = _load_metadata_files(sftp, meta_files)
    files = [
        file
        for file in files
        if file.type == "DocumentType" and file.parent_uuid != "trash"
    ]
    sftp.close()
    return files


def _load_metadata_files(
    sftp: paramiko.SSHClient, metadata_files: list[TmpMetadata]
) -> RemarkableFile:
    data = {
        Path(file.filename).stem: {
            **json.loads(sftp.open(str(FILES_ROOT / file.filename)).read()),
            "st_mtime": file.st_mtime,
        }
        for file in metadata_files
    }
    paths = _load_file_paths(data)

    return [
        RemarkableFile(
            uuid=uuid,
            last_modified=datetime.fromtimestamp(meta["st_mtime"]),
            parent_uuid=meta["parent"],
            name=meta["visibleName"],
            type=meta["type"],
            path=paths[uuid],
        )
        for uuid, meta in data.items()
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
                logger.warning(f"Page does not exist {page_path}")
                continue
            pdf_path = tmpdir / page_path.with_suffix(".pdf").name
            rm_to_pdf(tmpdir / page_path.name, pdf_path)
            with open(pdf_path, "rb") as f:
                data = f.read()
                page_data.append(
                    RemarkablePage(
                        page_idx=i,
                        parent=metadata_file,
                        uuid=page_path.stem,
                        pdf_data=data,
                        hash=sha256(data).hexdigest(),
                    )
                )
    sftp.close()
    return page_data
