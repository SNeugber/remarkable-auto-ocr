from dataclasses import dataclass
from enum import Enum
from hashlib import sha256
from pathlib import Path
import pandas as pd
from config import Config
from models import RemarkableFile
from loguru import logger


@dataclass
class ProcessingConfig:
    pdf_only: bool
    force_reprocess: bool
    prompt: str | None

    @property
    def prompt_hash(self) -> str | None:
        if self.prompt is None:
            return None
        return sha256(self.prompt.encode("utf-8")).hexdigest()


class ReprocessValues(Enum):
    ONCE = "once"
    ALWAYS = "always"


def _load_filters() -> tuple[pd.DataFrame | None, pd.DataFrame | None]:
    whitelist = blacklist = None
    if Path(Config.whitelist_path).exists():
        whitelist = pd.read_csv(Config.whitelist_path)
    if Path(Config.blacklist_path).exists():
        blacklist = pd.read_csv(Config.blacklist_path)
    return whitelist, blacklist


def _get_matches_in_dataframe(file: RemarkableFile, df: pd.DataFrame) -> pd.DataFrame:
    return df[df.path.apply(lambda path: str(file.path).startswith(path))]


def _get_processing_config_for_file(
    file: RemarkableFile, whitelist: pd.DataFrame, prompts: dict[str, str]
) -> ProcessingConfig | None:
    matches = _get_matches_in_dataframe(file, whitelist)
    if len(matches) == 0:
        return None
    most_specific = matches.iloc[matches.path.str.len().argmax()]
    prompt = Config.default_prompt
    if most_specific.prompt_path and not pd.isna(most_specific.prompt_path):
        if most_specific.prompt_path not in prompts:
            logger.error(
                f"Prompt file {most_specific.prompt_path} not found in prompts. Skipping processing for file {file.name}"
            )
            return None
        prompt = prompts[most_specific.prompt_path]
    force_reprocess = False
    if not pd.isna(most_specific.force_reprocess):
        reprocess_values = [e.value for e in ReprocessValues]
        if str(most_specific.force_reprocess).lower() not in reprocess_values:
            logger.error(
                f"Trying to force reprocessing of {file.path},\n"
                f"but incorrect reprocessing config given: {most_specific.force_reprocess}\n"
                f"Valid options are: {reprocess_values}.\n"
                f"Skipping file..."
            )
            return None
        force_reprocess = True
    return ProcessingConfig(
        pdf_only=bool(most_specific.pdf_only),
        prompt=prompt,
        force_reprocess=force_reprocess,
    )


def _load_prompts() -> dict[str, str]:
    prompts = {}
    prompts_dir = Path(Config.prompts_dir)
    if prompts_dir.exists():
        for path in Path(Config.prompts_dir).rglob("*.txt"):
            prompts[str(path.relative_to(prompts_dir))] = path.read_text()
    return prompts


def get_configs_for_files(
    files: list[RemarkableFile],
) -> dict[RemarkableFile, ProcessingConfig]:
    whitelist, blacklist = _load_filters()
    prompts = _load_prompts()
    configs = {}
    for file in files:
        if whitelist is not None:
            config = _get_processing_config_for_file(file, whitelist, prompts)
        else:
            config = ProcessingConfig(
                pdf_only=False, prompt=Config.default_prompt, force_reprocess=False
            )
        if (
            blacklist is not None
            and len(_get_matches_in_dataframe(file, blacklist)) > 0
        ):
            config = None
        if config is not None:
            configs[file] = config
    if whitelist is not None:
        whitelist = _update_reprocess_values(whitelist)
        whitelist.to_csv(Path(Config.whitelist_path), index=False)
    return configs


def _update_reprocess_values(df: pd.DataFrame) -> pd.DataFrame:
    df.loc[
        df.force_reprocess.astype(str).str.lower() == ReprocessValues.ONCE.value,
        "force_reprocess",
    ] = pd.NA
    return df
