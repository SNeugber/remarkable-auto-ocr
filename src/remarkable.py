from collections import namedtuple
from datetime import datetime
from io import BytesIO
import json
from pathlib import Path
import re
import tempfile
from loguru import logger
import pandas as pd
import rmc
from rmc.exporters.svg import PAGE_HEIGHT_PT, PAGE_WIDTH_PT
from pypdf import PdfReader, PdfWriter, PageObject, Transformation

import paramiko
from models import RemarkableFile, RemarkablePage
from config import Config
from contextlib import contextmanager
from collections.abc import Iterator
from hashlib import sha256

FILES_ROOT = Path("/home/root/.local/share/remarkable/xochitl/")
SVG_VIEWBOX_PATTERN = re.compile(
    r"^<svg .+ viewBox=\"([\-\d.]+) ([\-\d.]+) ([\-\d.]+) ([\-\d.]+)\">$"
)

TmpMetadata = namedtuple("Metadata", ["filename", "st_mtime"])


@contextmanager
def connect(retries: int = 5) -> Iterator[paramiko.SSHClient | None]:
    pk_file = Path(Config.ssh_key_path)
    if not pk_file.exists():
        raise FileNotFoundError(pk_file)
    loader = (
        paramiko.Ed25519Key if "ed25519" in pk_file.stem.lower() else paramiko.RSAKey
    )
    pkey = loader.from_private_key_file(pk_file)
    client = paramiko.SSHClient()
    policy = paramiko.AutoAddPolicy()
    client.set_missing_host_key_policy(policy)
    connected = False
    for _ in range(retries):
        try:
            client.connect(
                Config.remarkable_ip_address, username="root", pkey=pkey, timeout=5
            )
            connected = True
            break
        except TimeoutError:
            continue

    try:
        yield client if connected else None
    finally:
        client.close()


def get_files(
    client: paramiko.SSHClient,
) -> list[RemarkableFile]:
    sftp = client.open_sftp()
    files_df = pd.DataFrame(
        [attr.__dict__ for attr in sftp.listdir_attr(str(FILES_ROOT))]
    )
    meta_files = files_df[files_df.filename.str.endswith(".metadata")]
    pdf_file_uuids = set(
        files_df[files_df.filename.str.endswith(".pdf")].filename.apply(
            lambda p: Path(p).stem
        )
    )
    meta_files = [
        TmpMetadata(*row) for row in meta_files[["filename", "st_mtime"]].values
    ]
    files = _load_metadata_files(sftp, meta_files, pdf_file_uuids)
    files = [
        file
        for file in files
        if file.type == "DocumentType" and file.parent_uuid != "trash"
    ]
    sftp.close()
    return files


def _load_metadata_files(
    sftp: paramiko.SSHClient,
    metadata_files: list[TmpMetadata],
    pdf_file_uuids: set[str],
) -> RemarkableFile:
    data = {
        Path(file.filename).stem: {
            **json.loads(sftp.open(str(FILES_ROOT / file.filename)).read()),
            "st_mtime": file.st_mtime,
        }
        for file in metadata_files
    }
    paths = _load_file_paths(data)

    return [
        RemarkableFile(
            uuid=uuid,
            last_modified=datetime.fromtimestamp(meta["st_mtime"]),
            parent_uuid=meta["parent"],
            name=meta["visibleName"],
            type=meta["type"],
            path=paths[uuid],
            has_pdf=uuid in pdf_file_uuids,
        )
        for uuid, meta in data.items()
    ]


def _load_file_paths(
    files: dict[str, dict],
) -> dict[str, Path]:
    paths = {}
    for uuid, meta in files.items():
        path = [meta["visibleName"]]
        parent_uuid = meta["parent"]
        parent = files.get(parent_uuid)
        while parent:
            path.append(parent["visibleName"])
            parent = files.get(parent["parent"])
        paths[uuid] = Path("/".join(reversed(path)))
    return paths


def render_pages(
    client: paramiko.SSHClient, metadata_file: RemarkableFile
) -> list[RemarkablePage]:
    sftp = client.open_sftp()
    existing_pdf = None
    try:
        content_file = FILES_ROOT / (metadata_file.uuid + ".content")
        content = json.loads(sftp.open(str(content_file)).read())

        if metadata_file.has_pdf:
            existing_pdf_path = FILES_ROOT / (metadata_file.uuid + ".pdf")
            existing_pdf = PdfReader(BytesIO(sftp.open(str(existing_pdf_path)).read()))
    except IOError as e:
        logger.info(f"No content file for {metadata_file.uuid}.\n{e}")
        sftp.close()
        return []

    pages = content.get("cPages", {}).get("pages", [])
    page_paths = [
        FILES_ROOT / metadata_file.uuid / f"{page['id']}.rm" for page in pages
    ]
    existing_pdf_page_indexes = (
        # Page indexes in the original pdf, if this is an annotated PDF
        # "None" values indicate new remarkable pages added to the PDF
        [page.get("redir", {}).get("value", None) for page in pages]
        if existing_pdf
        else []
    )

    page_data = []
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        for i, page_path in enumerate(page_paths):
            blank_page = False
            try:
                sftp.get(str(page_path), str(tmpdir / page_path.name))
            except FileNotFoundError:
                if existing_pdf and existing_pdf_page_indexes[i] is not None:
                    blank_page = True
                else:
                    logger.warning(f"Page does not exist {page_path}")
                    continue
            pdf_path = tmpdir / page_path.with_suffix(".pdf").name
            if blank_page:
                writer = PdfWriter()
                writer.add_page(existing_pdf.pages[existing_pdf_page_indexes[i]])
                writer.write(pdf_path)
                writer.close()
            else:
                rmc.rm_to_pdf(tmpdir / page_path.name, pdf_path)
                if existing_pdf and existing_pdf_page_indexes[i] is not None:
                    _overlay(
                        existing=existing_pdf,
                        rm_page=tmpdir / page_path.name,
                        overlay=pdf_path,
                        page=existing_pdf_page_indexes[i],
                    )
            with open(pdf_path, "rb") as f:
                data = f.read()
                page_data.append(
                    RemarkablePage(
                        page_idx=i,
                        parent=metadata_file,
                        uuid=page_path.stem,
                        pdf_data=data,
                        hash=sha256(data).hexdigest(),
                    )
                )

    sftp.close()
    return page_data


def _overlay(existing: PdfReader, rm_page: Path, overlay: Path, page: int) -> None:
    """
    This function is intended to overlay annotations over existing PDF files.

    ⚠️ It is kind of broken, only works like 99% ish ⚠️
    The problem is that the pdf rendered by rmc is still using hardcoded
    values for the remarkable 2, whereas the paper pro has a different
    screen size/resolution/dpi.

    rmc also renders pdf cropped tight around the content, so we have to offset & scale them
    to match the original pdf's dimensions.

    Lastly merging protated dfs is causing issues, because it looks like the rmc-rendered pdf
    doesn't have the rotation set (correctly?), so when overlaying them naively one of them isn't
    rotated.

    Hence we basically:
    1. fix offset
    2. un-rotate
    3. scale
    4. re-rotate
    """

    existing_page = existing.pages[page]
    overlay_page = PdfReader(overlay).pages[0]

    rotation = existing_page.rotation
    if rotation:
        existing_page.transfer_rotation_to_content()

    w_bg, h_bg = existing_page.cropbox.width, existing_page.cropbox.height
    x_shift, y_shift, w_svg, h_svg = 0, 0, PAGE_WIDTH_PT, PAGE_HEIGHT_PT

    with tempfile.NamedTemporaryFile(suffix=".svg", mode="w") as tmp_svg:
        rmc.rm_to_svg(rm_page, tmp_svg.name)
        with open(tmp_svg.name, "r") as f:
            svg_content = f.readlines()
            for line in svg_content:
                res = SVG_VIEWBOX_PATTERN.match(line)
                if res is not None:
                    x_shift, y_shift = float(res.group(1)), float(res.group(2))
                    w_svg, h_svg = float(res.group(3)), float(res.group(4))
                    break

    width, height = max(w_svg, w_bg), max(h_svg, h_bg)
    merged_page = PageObject.create_blank_page(width=width, height=height)
    # compute position of svg and background in the new_page
    x_svg, y_svg = 0, 0
    x_bg, y_bg = 0, 0
    if w_svg > w_bg:
        x_bg = width / 2 - w_bg / 2 - (w_svg / 2 + x_shift)
    elif w_svg < w_bg:
        x_svg = width / 2 - w_svg / 2 + (w_svg / 2 + x_shift)
    if h_svg > h_bg:
        y_bg = height - h_bg + y_shift
    elif h_svg < h_bg:
        y_svg = height - h_svg - y_shift
    # merge background_page and svg_pdf_p
    merged_page.merge_transformed_page(
        existing_page, Transformation().translate(x_bg, y_bg)
    )
    merged_page.merge_transformed_page(
        overlay_page, Transformation().translate(x_svg, y_svg), expand=True
    )

    writer = PdfWriter()
    writer.add_page(merged_page)
    writer.write(overlay)
    writer.close()
