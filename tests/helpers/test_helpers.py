"""Helper objects to improve modularity of tests."""
from sqlalchemy import ForeignKey, Integer, String, select
from sqlalchemy.orm import mapped_column, relationship

from authanor.database.models import AuthorizedAccessMixin, Model, View


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
    alt_auth_entry = relationship(
        "AlternateAuthorizedEntry",
        back_populates="auth_entry",
        cascade="all, delete",
    )


class AlternateAuthorizedEntry(AuthorizedAccessMixin, Model):
    __tablename__ = "alt_authorized_entries"
    _user_id_join_chain = (AuthorizedEntry, Entry)
    # Columns
    p = mapped_column(Integer, primary_key=True)
    q = mapped_column(Integer, ForeignKey("authorized_entries.a"), nullable=False)
    # Relationships
    auth_entry = relationship("AuthorizedEntry", back_populates="alt_auth_entry")


class AlternateAuthorizedEntryView(AuthorizedAccessMixin, Model):
    __table__ = View(
        "alt_authorized_entries_view",
        Model.metadata,
        select(
            AlternateAuthorizedEntry.p.label("p"),
            AlternateAuthorizedEntry.q.label("q"),
            (AlternateAuthorizedEntry.p + AlternateAuthorizedEntry.q).label("r"),
        ),
    )
    _user_id_join_chain = (AuthorizedEntry, Entry)
