# tests/test_doc_parsing.py
from unittest.mock import MagicMock, patch

from src.rao import doc_parsing
from src.rao.models import ProcessingConfig, RemarkableFile, RemarkablePage


@patch("src.rao.doc_parsing.genai")
def test__pdf2md(mock_genai):
    mock_config = MagicMock()
    mock_config.google_api_key = "test_key"
    mock_config.model = "test_model"
    mock_config.backup_model = "backup_model"
    doc_parsing.Config = mock_config
    mock_response = MagicMock()
    mock_response.text = "test_markdown"
    mock_genai.GenerativeModel.return_value.generate_content.return_value = (
        mock_response
    )
    pdf_data = b"test_pdf_data"
    prompt = "test_prompt"

    md = doc_parsing._pdf2md(pdf_data, prompt)

    assert md == "test_markdown"
    mock_genai.configure.assert_called_once_with(api_key="test_key")
    mock_genai.GenerativeModel.assert_called_with("test_model")


@patch("src.rao.doc_parsing.genai")
def test__pdf2md_backup_model(mock_genai):
    mock_config = MagicMock()
    mock_config.google_api_key = "test_key"
    mock_config.model = "test_model"
    mock_config.backup_model = "backup_model"
    doc_parsing.Config = mock_config

    mock_response = MagicMock()
    mock_response.text = "test_markdown"

    # first call raises exception
    mock_genai.GenerativeModel.return_value.generate_content.side_effect = [
        Exception("Boom!"),
        mock_response,
    ]
    pdf_data = b"test_pdf_data"
    prompt = "test_prompt"

    md = doc_parsing._pdf2md(pdf_data, prompt)

    assert md == "test_markdown"
    mock_genai.configure.assert_called_once_with(api_key="test_key")
    assert mock_genai.GenerativeModel.call_count == 2
    mock_genai.GenerativeModel.assert_any_call("test_model")
    mock_genai.GenerativeModel.assert_called_with("backup_model")


@patch("src.rao.doc_parsing.genai")
@patch("src.rao.doc_parsing._pdf2md")
def test_pages_to_md(mock_pdf2md, mock_genai):
    mock_config = MagicMock()
    mock_config.google_api_key = "test_key"
    mock_config.model = "test_model"
    mock_config.backup_model = "backup_model"
    doc_parsing.Config = mock_config

    mock_page1 = RemarkablePage(
        file_name="file1.pdf",
        modified_client=123,
        page=1,
        page_idx=0,
        parent=RemarkableFile(name="file1", modified_client=1234),
    )
    mock_page2 = RemarkablePage(
        file_name="file2.pdf",
        modified_client=456,
        page=1,
        page_idx=1,
        parent=RemarkableFile(name="file2", modified_client=5678),
    )
    mock_pdf2md.side_effect = ["markdown1", "markdown2"]
    file_configs = {
        mock_page1.parent: ProcessingConfig(),
        mock_page2.parent: ProcessingConfig(),
    }

    rendered, failed = doc_parsing.pages_to_md([mock_page1, mock_page2, file_configs])

    assert rendered == {mock_page1: "markdown1", mock_page2: "markdown2"}
    assert failed == set()
    mock_pdf2md.assert_any_call(mock_page1.pdf_data, prompt="")
    mock_pdf2md.assert_any_call(mock_page2.pdf_data, prompt="")


@patch("src.rao.doc_parsing.genai")
@patch("src.rao.doc_parsing._pdf2md")
def test_pages_to_md_failure(mock_pdf2md, mock_genai):
    mock_config = MagicMock()
    mock_config.google_api_key = "test_key"
    mock_config.model = "test_model"
    mock_config.backup_model = "backup_model"
    doc_parsing.Config = mock_config

    mock_page1 = RemarkablePage(
        file_name="file1.pdf",
        modified_client=123,
        page=1,
        page_idx=0,
        parent=RemarkableFile(name="file1", modified_client=1234),
    )
    mock_page2 = RemarkablePage(
        file_name="file2.pdf",
        modified_client=456,
        page=1,
        page_idx=1,
        parent=RemarkableFile(name="file2", modified_client=5678),
    )
    mock_pdf2md.side_effect = ["markdown1", None]
    file_configs = {
        mock_page1.parent: ProcessingConfig(),
        mock_page2.parent: ProcessingConfig(),
    }

    rendered, failed = doc_parsing.pages_to_md([mock_page1, mock_page2], file_configs)

    assert rendered == {mock_page1: "markdown1"}
    assert failed == {mock_page2}
    mock_pdf2md.assert_any_call(mock_page1.pdf_data, prompt="")
    mock_pdf2md.assert_any_call(mock_page2.pdf_data, prompt="")


@patch("src.rao.doc_parsing.genai")
@patch("src.rao.doc_parsing._pdf2md")
def test_pages_to_md_pdf_only(mock_pdf2md, mock_genai):
    mock_config = MagicMock()
    mock_config.google_api_key = "test_key"
    mock_config.model = "test_model"
    mock_config.backup_model = "backup_model"
    doc_parsing.Config = mock_config

    mock_page1 = RemarkablePage(
        file_name="file1.pdf",
        modified_client=123,
        page=1,
        page_idx=0,
        parent=RemarkableFile(name="file1", modified_client=1234),
    )

    file_configs = {
        mock_page1.parent: ProcessingConfig(pdf_only=True),
    }

    rendered, failed = doc_parsing.pages_to_md([mock_page1], file_configs)

    assert rendered == {}
    assert failed == set()
    mock_pdf2md.assert_not_called()


def test__postprocess():
    md = "```markdown\n\nsome content\n\n```"
    page = RemarkablePage(
        file_name="file1.pdf",
        modified_client=123,
        page=1,
        page_idx=0,
        parent=RemarkableFile(name="file1", modified_client=1234),
    )
    processed_md = doc_parsing._postprocess(md, page)
    assert processed_md == "some content"

    md = "```\nsome content\n```"
    processed_md = doc_parsing._postprocess(md, page)
    assert processed_md == "some content"

    md = "\nsome content\n"
    processed_md = doc_parsing._postprocess(md, page)
    assert processed_md == "some content"
