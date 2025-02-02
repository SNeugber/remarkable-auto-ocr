from collections import defaultdict
from io import BytesIO
from pathlib import Path
from models import RemarkableFile, RemarkablePage
from config import Config
from pypdf import PdfWriter


def save(
    pages: dict[RemarkablePage, str],
) -> dict[RemarkableFile, list[RemarkablePage]]:
    pages_with_md = {p: md for p, md in pages.items() if md is not None}
    saved_md_files = _save_mds_to_disk(pages_with_md)
    saved_pdf_files = _save_pdfs_to_disk(list(pages.keys()))
    # saved_pdf_files: dict[RemarkableFile, list[RemarkablePage]] = _save_md_to_disk(md_files)
    if Config.git_repo_path:
        _sync_with_subrepo(saved_md_files)
    if Config.gdrive_folder_path:
        _copy_to_gdrive_folder(saved_pdf_files)
    return {**saved_pdf_files, **saved_md_files}


def _combine_md_pages(file_name: str, pages: dict[RemarkablePage, str]) -> str:
    lines = [f"# {file_name}\n"]
    pages_sorted = sorted(pages.keys(), key=lambda p: p.page_idx)
    for page in pages_sorted:
        lines.append(f"## Page {page.page_idx + 1} - [{page.uuid}]\n")
        for line in pages[page].split("\n"):
            if line.startswith("#"):
                line = "##" + line
            lines.append(line)
    return "\n".join(lines)


def _save_mds_to_disk(
    md_files: dict[RemarkablePage, str],
) -> dict[RemarkableFile, list[RemarkablePage]]:
    base_dir = Path(Config.render_path) / "md"
    saved = {}

    pages_per_file: dict[RemarkableFile, dict[RemarkablePage, str]] = defaultdict(dict)
    for page in md_files.keys():
        pages_per_file[page.parent][page] = md_files[page]

    for parent, pages in pages_per_file.items():
        parent_path = base_dir / parent.path
        target_dir = parent_path.parent
        target_dir.mkdir(exist_ok=True, parents=True)
        file_name = parent_path.stem
        # TODO: load existing data if it exists & merge with new data
        md_combined = _combine_md_pages(file_name, pages)
        md_path = target_dir / f"{file_name}.md"
        with open(md_path, "w") as f:
            f.write(md_combined)
        saved[parent] = pages
    return saved


def _save_pdfs_to_disk(pages: list[RemarkablePage]) -> bytes:
    base_dir = Path(Config.render_path) / "pdf"
    saved = {}

    pages_per_file: dict[RemarkableFile, list[RemarkablePage]] = defaultdict(list)
    for page in pages:
        pages_per_file[page.parent].append(page)

    for parent, pages in pages_per_file.items():
        parent_path = base_dir / parent.path
        target_dir = parent_path.parent
        target_dir.mkdir(exist_ok=True, parents=True)
        file_name = parent_path.stem
        # TODO: load existing data if it exists & merge with new data somehow...
        _save_combined_pdf(target_dir / f"{file_name}.pdf", pages)
        saved[parent] = pages
    return saved


def _save_combined_pdf(pdf_path: Path, pages: list[RemarkablePage]) -> None:
    writer = PdfWriter()
    for page in sorted(pages, key=lambda p: p.page_idx):
        writer.append(BytesIO(page.pdf_data))
    writer.write(pdf_path)
    writer.close()


def _sync_with_subrepo():
    pass


def _copy_to_gdrive_folder():
    pass
