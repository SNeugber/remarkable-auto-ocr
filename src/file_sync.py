from collections import defaultdict
from pathlib import Path
from models import RemarkableFile, RemarkablePage
from config import Config


def _build_directory_structure(
    files: list[RemarkableFile],
) -> dict[str, Path]:
    files_map = {file.uuid: file for file in files}
    paths = dict()
    # I want to turn this into a dict of file -> file path
    for file in files:
        path = [file.name]
        parent = files_map.get(file.parent_uuid)
        while parent:
            path.append(parent.name)
            parent = files_map.get(parent.parent_uuid)
        paths[file.uuid] = Path("/".join(reversed(path)))
    return paths


def save(
    files: list[RemarkableFile], md_files: dict[RemarkablePage, str]
) -> dict[RemarkableFile, list[RemarkablePage]]:
    dir_structure = _build_directory_structure(files)
    saved: dict[str, list[RemarkablePage]] = _save_to_disk(md_files, dir_structure)
    saved_files = {f: saved[f.uuid] for f in files if f.uuid in saved.keys()}
    if Config.GitRepoPath:
        _sync_with_subrepo([f for f in saved.values() if f.suffix == ".md"])
    if Config.GDriveFolderPath:
        _copy_to_gdrive_folder([f for f in saved.values() if f.suffix == ".pdf"])
    return saved_files


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
    dir_structure: dict[str, Path],
) -> dict[str, list[RemarkablePage]]:
    base_dir = Path("./data/renders")
    saved = {}

    pages_per_file = defaultdict(dict)
    for page in md_files.keys():
        pages_per_file[page.parent_uuid][page] = md_files[page]

    for pages in pages_per_file.values():
        meta = page.parent_uuid
        meta_dir = (base_dir / dir_structure[meta]).parent
        meta_dir.mkdir(exist_ok=True, parents=True)
        file_name = dir_structure[meta].stem
        # TODO: load existing data if it exists & merge with new data
        md_combined = _combine_pages(file_name, pages)
        md_path = meta_dir / f"{file_name}.md"
        with open(md_path, "w") as f:
            f.write(md_combined)
        saved[file_name] = pages
    return saved


def _sync_with_subrepo():
    pass


def _copy_to_gdrive_folder():
    pass
