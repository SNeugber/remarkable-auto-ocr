from dataclasses import dataclass
import datetime
from sqlalchemy import Column, String, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped
from sqlalchemy.orm import mapped_column
from sqlalchemy.orm import relationship

Base = declarative_base()


class Metadata(Base):
    __tablename__ = "metadata"

    uuid = Column(String, primary_key=True)
    visible_name = Column(String)
    last_modified = Column(DateTime)
    parent_uuid = Column(String)
    type = Column(String)
    pages: Mapped[list["Page"]] = relationship()


class Page(Base):
    __tablename__ = "page"

    uuid = Column(String, primary_key=True)
    hash = Column(String)
    parent_uuid: Mapped[String] = mapped_column(ForeignKey("metadata.uuid"))


@dataclass(eq=True, frozen=True)
class RemarkablePage:
    uuid: str
    hash: str
    parent_uuid: str
    page_idx: int
    data: bytes


@dataclass(eq=True, frozen=True)
class RemarkableFile:
    uuid: str
    name: str
    type: str
    parent_uuid: str
    last_modified: datetime.date
