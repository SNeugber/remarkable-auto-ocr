from pathlib import Path
import pandas as pd


def load() -> pd.DataFrame:
    if not Path("./db.csv").exists():
        pd.DataFrame(columns=["name", "uuid", "parent_uuid", "last_synced"]).to_csv(
            "./db.csv", index=False
        )

    return pd.read_csv("./db.csv")
