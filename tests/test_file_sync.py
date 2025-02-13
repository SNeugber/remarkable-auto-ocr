# tests/test_file_sync.py
from pathlib import Path
from unittest.mock import patch

from rao import file_sync
from rao.models import RemarkableFile, RemarkablePage


def test__combine_md_pages():
    file_name = "test_file"
    page1 = RemarkablePage(
        page_idx=0, uuid="uuid1", parent=RemarkableFile(name="test_file")
    )
    page2 = RemarkablePage(
        page_idx=1, uuid="uuid2", parent=RemarkableFile(name="test_file")
    )
    pages = {page1: "page1 content", page2: "page2 content"}
    existing_md = None

    md = file_sync._combine_md_pages(file_name, pages, existing_md)

    assert "# test_file" in md
    assert "## Page 1 - [uuid1]" in md
    assert "page1 content" in md
    assert "## Page 2 - [uuid2]" in md
    assert "page2 content" in md


# Example test for _dir_to_md_tree


# Mock pathname2url for consistent testing across systems
@patch("os.path.exists", return_value=True)  # mock the directory and files
@patch(
    "rao.file_sync.pathname2url", return_value="/test/path/file.md"
)  # Mock os.path.relpath
def test__dir_to_md_tree(mock_url, mock_exists):
    root_path = Path("./test_dir")

    # create dummy files and dir, so we can use it for the function calls below
    (root_path / "file1.md").touch()
    (root_path / "subdir").mkdir()
    (root_path / "subdir" / "file2.md").touch()

    lines = file_sync._dir_to_md_tree(root_path, root_path)

    assert "* [file1.md](/test/path/file.md)" in lines
    assert "* [subdir/](subdir)" in lines
    assert "  * [file2.md](/test/path/file.md)" in lines

    # cleanup
    (root_path / "file1.md").unlink()
    (root_path / "subdir" / "file2.md").unlink()
    (root_path / "subdir").rmdir()
    root_path.rmdir()
