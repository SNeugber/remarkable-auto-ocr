from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import sessionmaker
from datetime import datetime
from models import Metadata, Base


def get_engine() -> Engine:
    db_dir = Path("./data")
    db_dir.mkdir(exist_ok=True)
    engine = create_engine("sqlite:///data/db.sqlite", echo=True)
    Base.metadata.create_all(engine)
    return engine


def parse_files(engine: Engine, files: list[tuple[str, dict]]):
    Session = sessionmaker(bind=engine)
    session = Session()

    for file_name, file_contents in files:
        metadata = Metadata(
            id=file_name,
            created_time=datetime.fromtimestamp(file_contents["createdTime"]),
            last_modified=datetime.fromtimestamp(file_contents["lastModified"]),
            parent_id=file_contents["parent"],
            type=file_contents["type"],
            visible_name=file_contents["visibleName"],
        )
        session.add(metadata)

    session.commit()
    session.close()
