from collections import defaultdict
from io import BytesIO
from pathlib import Path
import re
import shutil
import subprocess
from models import RemarkableFile, RemarkablePage
from config import Config
from pypdf import PdfWriter
from loguru import logger
from urllib.request import pathname2url

PAGE_SEPARATOR = re.compile(r"^## Page \d+ - \[[0-9a-f\-]+\]$")


def save(
    all_pages: list[RemarkablePage],
    rendered_pages: dict[RemarkablePage, str],
) -> dict[RemarkableFile, list[RemarkablePage]]:
    _save_mds_to_disk(rendered_pages)
    saved_pdf_files = _save_pdfs_to_disk(all_pages)
    if Config.git_repo_path:
        _sync_with_subrepo()
    if Config.gdrive_folder_path:
        _copy_to_gdrive_folder(saved_pdf_files)
    return saved_pdf_files


def _split_md_into_pages(md: str) -> dict[int, list[str]]:
    pages = {}
    current_page = None
    current_page_lines = []
    for line in md.split("\n"):
        page_sep = re.findall(PAGE_SEPARATOR, line)
        if len(page_sep) > 1:
            raise ValueError("Multiple page separators found in line.")
        if len(page_sep) > 0:
            pages[current_page] = current_page_lines
            page_sep = page_sep[0]
            page_num = int(page_sep.split(" - ")[0].split("## Page ")[1])
            current_page = page_num
            current_page_lines = []
        current_page_lines.append(line)
    pages[current_page] = current_page_lines
    del pages[None]  # Remove anything before the first page
    return pages


def _combine_md_pages(
    file_name: str, pages: dict[RemarkablePage, str], existing_md: str | None
) -> str:
    existing_pages = _split_md_into_pages(existing_md) if existing_md else {}
    new_pages = {p.page_idx + 1: p for p in pages.keys()}
    all_page_numbers = set(existing_pages.keys()) | set(new_pages.keys())

    lines = [f"# {file_name}\n"]
    for page_idx in sorted(all_page_numbers):
        if page_idx in new_pages:
            page = new_pages[page_idx]
            lines.append(f"## Page {page_idx} - [{page.uuid}]\n")
            for line in pages[page].split("\n"):
                if line.startswith("#"):
                    line = "##" + line
                lines.append(line)
            lines.append("\n")
            continue
        if page_idx in existing_pages:
            lines += existing_pages[page_idx]
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
        md_path = target_dir / f"{file_name}.md"
        existing = md_path.read_text() if md_path.exists() else None
        md_combined = _combine_md_pages(file_name, pages, existing)
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
    base_dir = Path(Config.render_path) / "md"
    shutil.copytree(
        base_dir, Path(Config.git_repo_path) / "documents", dirs_exist_ok=True
    )
    _save_markdown_repo_readme_file()
    try:
        subprocess.run(["git", "add", "."], cwd=Config.git_repo_path, check=True)
        subprocess.run(
            ["git", "commit", "-m", "Update files"],
            cwd=Config.git_repo_path,
            check=True,
        )
        subprocess.run(["git", "push"], cwd=Config.git_repo_path, check=True)
    except subprocess.CalledProcessError as e:
        logger.error(f"Unable to sync files with with subrepo: {e}")


def _save_markdown_repo_readme_file():
    readme_path = [
        p for p in Path(Config.git_repo_path).glob("*.md") if p.stem.lower() == "readme"
    ]
    DOCS_HEADER = "\n\n## Documents\n\n"
    if not readme_path:
        readme_path = Path(Config.git_repo_path) / "README.md"
        readme = "# Markdown Documents from Remarkable"
    else:
        readme_path = readme_path[0]
        readme = readme_path.read_text()
        readme = readme.split(DOCS_HEADER)[0]

    doc_tree = "\n".join(
        _dir_to_md_tree(
            Path(Config.git_repo_path), Path(Config.git_repo_path) / "documents"
        )
    )
    combined = f"{readme}{DOCS_HEADER}{doc_tree}"
    readme_path.write_text(combined)


def _dir_to_md_tree(root_path: Path, path: Path, prefix="  "):
    indent = "  "
    item_prefix = "* "

    paths = list(path.glob("*"))
    files = [path for path in paths if path.is_file()]
    files.sort(key=lambda f: f.name)
    lines = [
        f"{prefix}{item_prefix}[{file.name}]({pathname2url(str(file.relative_to(root_path)))})"
        for file in files
    ]

    dirs = [path for path in paths if path.is_dir()]
    dirs.sort(key=lambda d: d.name)
    for dir in dirs:
        lines.append(
            f"{prefix}{item_prefix}[{dir.name}/]({dir.relative_to(root_path)})"
        )
        lines += _dir_to_md_tree(root_path, dir, prefix + indent)
    return lines


def _copy_to_gdrive_folder():
    pass
