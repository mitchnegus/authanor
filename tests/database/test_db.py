"""Tests for the basic database objects."""


def test_database(app):
    table_names = ("entries", "authorized_entries", "alt_authorized_entries")
    assert all(name in app.db.tables.keys() for name in table_names)
