from datetime import datetime
import json
from pathlib import Path
import pandas as pd

import paramiko
from models import RemarkableFile
from config import Config


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


def load_file(
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


def get_files(
    client: paramiko.SSHClient,
    files_root: Path = Path("/home/root/.local/share/remarkable/xochitl/"),
) -> list[RemarkableFile]:
    sftp = client.open_sftp()
    files_df = pd.DataFrame(
        [attr.__dict__ for attr in sftp.listdir_attr(str(files_root))]
    )
    meta_files = files_df[files_df.filename.str.endswith(".metadata")]
    files = list(
        meta_files.apply(
            lambda file: load_file(sftp, files_root / file.filename, file.st_mtime),
            axis=1,
        )
    )
    return files
