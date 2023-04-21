"""Helper objects to improve modularity of tests."""
from sqlalchemy import ForeignKey, Integer, String
from sqlalchemy.orm import mapped_column, relationship

from authanor.database.models import AuthorizedAccessMixin, Model


class Entry(Model):
    __tablename__ = "entries"
    # Columns
    x = mapped_column(Integer, primary_key=True)
    y = mapped_column(String, nullable=False)
    user_id = mapped_column(Integer, nullable=False)
    # Relationships
    authorized_entries = relationship(
        "AuthorizedEntry",
        back_populates="entry",
        cascade="all, delete",
    )


class AuthorizedEntry(AuthorizedAccessMixin, Model):
    __tablename__ = "authorized_entries"
    _user_id_join_chain = (Entry,)
    # Columns
    a = mapped_column(Integer, primary_key=True)
    b = mapped_column(String, nullable=True)
    c = mapped_column(Integer, ForeignKey("entries.x"), nullable=False)
    # Relationships
    entry = relationship("Entry", back_populates="authorized_entries")
