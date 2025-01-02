"""
Helper tools to improve testing of authorized database interactions.
"""

import textwrap
from pprint import pformat

import pytest
from sqlalchemy import inspect, select
from sqlalchemy.sql.expression import func
from werkzeug.exceptions import NotFound


class TestHandler:
    """A base class for testing database handlers."""

    @pytest.fixture(autouse=True)
    def _get_app(self, app):
        # Use the client fixture in route tests
        self._app = app

    @staticmethod
    def _format_reference_comparison(references, entries):
        default_indent = "\t\t       "
        wrap_kwargs = {
            "initial_indent": default_indent,
            "subsequent_indent": f"{default_indent} ",
        }
        references_string = textwrap.fill(pformat(references, depth=1), **wrap_kwargs)
        entries_string = textwrap.fill(pformat(entries, depth=1), **wrap_kwargs)
        return (
            f"\n\t     references:\n{references_string}"
            f"\n\t        entries:\n{entries_string}"
        )

    @staticmethod
    def assert_entry_matches(entry, reference):
        assert isinstance(entry, type(reference))
        for column in inspect(type(entry)).columns:
            field = column.name
            assert getattr(entry, field) == getattr(reference, field), (
                "A field in the entry does not match the reference"
                f"\n\treference: {reference}"
                f"\n\t    entry: {entry}"
            )

    @classmethod
    def assert_entries_match(cls, entries, references, order=False):
        entries = list(entries)
        references = list(references)
        if references and not order:
            # Order does not matter, so sort both entries and references by ID
            primary_key = inspect(type(references[0])).primary_key[0].name
            entries = sorted(entries, key=lambda entry: getattr(entry, primary_key))
            references = sorted(
                references, key=lambda reference: getattr(reference, primary_key)
            )
        assert len(entries) == len(references), (
            "The number of references is not the same as the number of entries"
            f"\n\treference count: {len(references)}"
            f"\n\t    entry count: {len(entries)}\n"
            f"{cls._format_reference_comparison(references, entries)}"
        )
        # Compare the list elements
        for entry, reference in zip(entries, references):
            cls.assert_entry_matches(entry, reference)

    def assert_number_of_matches(self, number, field, *criteria):
        query = select(func.count(field))
        if criteria:
            query = query.where(*criteria)
        count = self._app.db.session.execute(query).scalar()
        assert count == number, (
            "The number of matches found does not match the number of matches expected"
            f"\n\texpected matches: {number}"
            f"\n\t   found matches: {count}"
        )

    def assert_invalid_user_entry_add_fails(self, handler, mapping):
        # Count the original number of entries
        query = select(func.count(handler.model.primary_key_field))
        entry_count = self._app.db.session.execute(query).scalar()
        # Ensure that the mapping cannot be added for the invalid user
        with pytest.raises(NotFound):
            handler.add_entry(**mapping)
        # Rollback and ensure that an entry was not added
        self._app.db.close()
        self.assert_number_of_matches(entry_count, handler.model.primary_key_field)

    def assert_entry_deletion_succeeds(self, handler, entry_id):
        handler.delete_entry(entry_id)
        # Check that the entry was deleted
        self.assert_number_of_matches(
            0,
            handler.model.primary_key_field,
            handler.model.primary_key_field == entry_id,
        )
