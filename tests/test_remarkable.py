# Example test for test remarkable.py
from unittest.mock import MagicMock

import pandas as pd

from rao import remarkable


def test__load_metadata_files():
    mock_sftp = MagicMock()

    mock_file = MagicMock()
    mock_file.read.return_value = (
        b'{"visibleName": "test_file", "parent":"uuid_parent", "type":"document"}'
    )
    mock_sftp.open.return_value = mock_file

    data = {
        "filename": ["uuid1.metadata", "uuid1.content", "uuid2.metadata"],
        "st_mtime": [1678886400, 1678886400, 1678886400],
    }
    df = pd.DataFrame(data)

    files = remarkable._load_metadata_files(mock_sftp, df)

    assert len(files) == 2
    assert files[0].name == "test_file"
    assert files[0].parent_uuid == "uuid_parent"
    assert files[0].type == "document"
