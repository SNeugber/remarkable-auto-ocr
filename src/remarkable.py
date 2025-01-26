from datetime import datetime
import json
from pathlib import Path
import tempfile
from zipfile import ZipFile
import zipfile
import pandas as pd
from rmrl import render
from rmrl.sources import FSSource

import paramiko
from models import RemarkableFile
from config import Config
import stat

FILES_ROOT = Path("/home/root/.local/share/remarkable/xochitl/")


def open_connection() -> paramiko.SSHClient:
    pk_file = Path(Config.SSHKeyPath)
    if not pk_file.exists():
        raise FileNotFoundError(pk_file)
    loader = paramiko.Ed25519Key if "ed25519" in pk_file.stem.lower() else paramiko.RSAKey
    pkey = loader.from_private_key_file(pk_file)
    client = paramiko.SSHClient()
    policy = paramiko.AutoAddPolicy()
    client.set_missing_host_key_policy(policy)
    client.connect(Config.RemarkableIPAddress, username="root", pkey=pkey)
    return client


def load_file_metadata(
    sftp: paramiko.SSHClient, file_path: Path, last_modified: int
) -> RemarkableFile:
    content = json.loads(sftp.open(str(file_path)).read())
    return RemarkableFile(
        uuid=file_path.stem,
        last_modified=datetime.fromtimestamp(last_modified),
        parent_uuid=content["parent"],
        name=content["visibleName"],
        type=content["type"],
    )

def render_pdf(file: RemarkableFile, client: paramiko.SSHClient) -> ZipFile:
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)

        sftp = client.open_sftp()
        meta_files = [f for f in sftp.listdir(str(FILES_ROOT)) if file.uuid in f]
        dirs_to_copy = []
        for meta_file in meta_files:
            fileattr = sftp.lstat(str(FILES_ROOT / meta_file))
            if stat.S_ISDIR(fileattr.st_mode):
                dirs_to_copy.append(meta_file)
                continue
            sftp.get(str(FILES_ROOT / meta_file), str(tmpdir / meta_file))

        while len(dirs_to_copy):
            directory = dirs_to_copy.pop(0)
            content_files = sftp.listdir(str(FILES_ROOT / directory))
            content_dir = tmpdir / directory
            content_dir.mkdir(parents=True)
            for content_file in content_files:
                fileattr = sftp.lstat(str(FILES_ROOT / directory / content_file))
                if stat.S_ISDIR(fileattr.st_mode):
                    dirs_to_copy.append(Path(directory) / content_file)
                    continue
                sftp.get(str(FILES_ROOT / directory / content_file), str(content_dir / content_file))

        output = render(str(tmpdir / file.uuid))  # TODO patch the issue here in fork and install from there...
        return output.read()

        

            


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
            lambda file: load_file_metadata(sftp, FILES_ROOT / file.filename, file.st_mtime),
            axis=1,
        )
    )
    return files
