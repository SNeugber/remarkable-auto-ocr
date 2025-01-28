from dataclasses import dataclass
import datetime
from sqlalchemy import Column, String, DateTime
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()


class Metadata(Base):
    __tablename__ = "metadata"

    uuid = Column(String, primary_key=True)
    visible_name = Column(String)
    last_modified = Column(DateTime)
    parent_uuid = Column(String)
    type = Column(String)


@dataclass
class RemarkablePage:
    data: bytes
    hash: str


@dataclass
class RemarkableFile:
    uuid: str
    name: str
    type: str
    parent_uuid: str
    last_modified: datetime.date
