# tests/test_file_sync.py
from pathlib import Path
from unittest.mock import MagicMock, patch

from rao import file_sync
from rao.models import RemarkablePage


def test__combine_md_pages():
    file = MagicMock()
    file.name = "test_file"
    page1 = RemarkablePage(
        page_idx=0, uuid="uuid1", parent=file, hash="hash1", pdf_data=b""
    )
    page2 = RemarkablePage(
        page_idx=1, uuid="uuid2", parent=file, hash="hash2", pdf_data=b""
    )
    pages = {page1: "page1 content", page2: "page2 content"}
    existing_md = None

    md = file_sync._combine_md_pages(file.name, pages, existing_md)

    assert "# test_file" in md
    assert "## Page 1 - [uuid1]" in md
    assert "page1 content" in md
    assert "## Page 2 - [uuid2]" in md
    assert "page2 content" in md


@patch("os.path.exists", return_value=True)
@patch("rao.file_sync.pathname2url", return_value="/test/path/file.md")
def test__dir_to_md_tree(mock_url: MagicMock, mock_exists: MagicMock, tmp_path: Path):
    root_path = tmp_path

    # create dummy files and dir, so we can use it for the function calls below
    (root_path / "file1.md").touch()
    (root_path / "subdir").mkdir()
    (root_path / "subdir" / "file2.md").touch()

    lines = file_sync._dir_to_md_tree(root_path, root_path)

    assert "  * [file1.md](/test/path/file.md)" in lines
    assert "  * [subdir/](subdir)" in lines
    assert "    * [file2.md](/test/path/file.md)" in lines
