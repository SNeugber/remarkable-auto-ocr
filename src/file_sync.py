from collections import defaultdict
from pathlib import Path
from models import RemarkableFile, RemarkablePage
from config import Config


def save(
    files: list[RemarkableFile], md_files: dict[RemarkablePage, str]
) -> dict[RemarkableFile, list[RemarkablePage]]:
    saved: dict[RemarkableFile, list[RemarkablePage]] = _save_to_disk(md_files, files)
    if Config.GitRepoPath:
        _sync_with_subrepo([f for f in saved.values() if f.suffix == ".md"])
    if Config.GDriveFolderPath:
        _copy_to_gdrive_folder([f for f in saved.values() if f.suffix == ".pdf"])
    return saved


def _combine_pages(file_name: str, pages: dict[RemarkablePage, str]) -> str:
    lines = [f"# {file_name}\n"]
    for page, md_data in pages.items():
        lines.append(f"## Page {page.page_idx + 1} - [{page.uuid}]\n")
        for line in md_data.split("\n"):
            if line.startswith("#"):
                line = "##" + line
            lines.append(line)
    return "\n".join(lines)


def _save_to_disk(
    md_files: dict[RemarkablePage, str],
    files: list[RemarkableFile],
) -> dict[RemarkableFile, list[RemarkablePage]]:
    base_dir = Path("./data/renders")
    saved = {}
    files_lookup = {file.uuid: file for file in files}

    pages_per_file = defaultdict(dict)
    for page in md_files.keys():
        pages_per_file[page.parent_uuid][page] = md_files[page]

    for pages in pages_per_file.values():
        parent = files_lookup[page.parent_uuid]
        target_dir = (base_dir / parent.path).parent
        target_dir.mkdir(exist_ok=True, parents=True)
        file_name = Path(parent.name).stem
        # TODO: load existing data if it exists & merge with new data
        md_combined = _combine_pages(file_name, pages)
        md_path = target_dir / f"{file_name}.md"
        with open(md_path, "w") as f:
            f.write(md_combined)
        saved[parent] = pages
    return saved


def _sync_with_subrepo():
    pass


def _copy_to_gdrive_folder():
    pass
