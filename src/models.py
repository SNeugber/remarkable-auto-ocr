from sqlalchemy import Column, String, DateTime
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()


class Metadata(Base):
    __tablename__ = "metadata"

    id = Column(String, primary_key=True)
    visible_name = Column(String)
    created_time = Column(DateTime)
    last_modified = Column(DateTime)
    parent_id = Column(String)
    type = Column(String)
