"""Tests for the database handlers."""
from contextlib import contextmanager
from unittest.mock import Mock, patch

import pytest
from sqlalchemy.exc import IntegrityError
from werkzeug.exceptions import NotFound

from authanor.database.handler import (
    DatabaseHandler,
    DatabaseViewHandler,
    QueryCriteria,
)
from authanor.test.helpers import TestHandler

from ..helpers import (
    AlternateAuthorizedEntry,
    AlternateAuthorizedEntryView,
    AuthorizedEntry,
    Entry,
)


@contextmanager
def mocked_user(user_id):
    with patch("authanor.database.handler.g") as mock_global_namespace:
        with patch("authanor.database.models.g", new=mock_global_namespace):
            mock_global_namespace.user = Mock(id=1)
            yield


class EntryHandler(DatabaseHandler, model=Entry):
    """A minimal database handler for testing."""


@pytest.fixture
def entry_handler(client_context):
    with mocked_user(user_id=1):
        yield EntryHandler


class AuthorizedEntryHandler(DatabaseHandler, model=AuthorizedEntry):
    """A minimal database handler for testing."""


@pytest.fixture
def authorized_entry_handler(client_context):
    with mocked_user(user_id=1):
        yield AuthorizedEntryHandler


@pytest.fixture
def criteria(request):
    if request.param is None:
        return None
    return request.getfixturevalue(request.param)


@pytest.fixture
def entry_criteria_x_single():
    criteria = QueryCriteria()
    criteria.add_match_filter(Entry, "x", 2)
    return criteria


@pytest.fixture
def entry_criteria_x_multiple():
    criteria = QueryCriteria()
    criteria.add_match_filter(Entry, "x", (2, 3))
    return criteria


@pytest.fixture
def entry_criteria_x_empty():
    criteria = QueryCriteria()
    criteria.add_match_filter(Entry, "x", 4)
    return criteria


@pytest.fixture
def authorized_entry_criteria_b_single():
    criteria = QueryCriteria()
    criteria.add_match_filter(AuthorizedEntry, "b", "two")
    return criteria


@pytest.fixture
def authorized_entry_criteria_b_multiple():
    criteria = QueryCriteria()
    criteria.add_match_filter(AuthorizedEntry, "b", ("two", "three"))
    return criteria


@pytest.fixture
def authorized_entry_criteria_b_empty():
    criteria = QueryCriteria()
    criteria.add_match_filter(AuthorizedEntry, "b", ("four"))
    return criteria


class TestDatabaseHandler(TestHandler):
    # Reference only includes authorized entries accessible to user ID 1
    db_reference = [
        Entry(x=1, y="ten", user_id=1),
        Entry(x=2, y="eleven", user_id=1),
        Entry(x=3, y="twenty", user_id=2),
        AuthorizedEntry(a=1, b="one", c=1),
        AuthorizedEntry(a=2, b="two", c=1),
    ]

    def test_initialization(self, entry_handler):
        assert entry_handler.model == Entry
        assert entry_handler.table.name == "entries"
        assert entry_handler.user_id == 1

    @pytest.mark.parametrize(
        "criteria, reference_entries",
        [
            [None, db_reference[:3]],
            ["entry_criteria_x_single", db_reference[1:2]],
            ["entry_criteria_x_multiple", db_reference[1:3]],
        ],
        indirect=["criteria"],
    )
    def test_get_entries(self, entry_handler, criteria, reference_entries):
        entries = entry_handler.get_entries(criteria=criteria)
        self.assert_entries_match(entries, reference_entries)

    @pytest.mark.parametrize(
        "criteria, reference_entries",
        [
            [None, db_reference[3:5]],
            ["authorized_entry_criteria_b_single", db_reference[4:5]],
            ["authorized_entry_criteria_b_multiple", db_reference[4:5]],
        ],
        indirect=["criteria"],
    )
    def test_get_authorized_entries(
        self, authorized_entry_handler, criteria, reference_entries
    ):
        authorized_entries = authorized_entry_handler.get_entries(criteria=criteria)
        self.assert_entries_match(authorized_entries, reference_entries)

    @pytest.mark.parametrize(
        "entry_id, reference_entry", [[1, db_reference[0]], [3, db_reference[2]]]
    )
    def test_get_entry(self, entry_handler, entry_id, reference_entry):
        entry = entry_handler.get_entry(entry_id)
        self.assert_entry_matches(entry, reference_entry)

    @pytest.mark.parametrize(
        "authorized_entry_id, reference_entry",
        [[1, db_reference[3]], [2, db_reference[4]]],
    )
    def test_get_authorized_entry(
        self, authorized_entry_handler, authorized_entry_id, reference_entry
    ):
        authorized_entry = authorized_entry_handler.get_entry(authorized_entry_id)
        self.assert_entry_matches(authorized_entry, reference_entry)

    @pytest.mark.parametrize(
        "authorized_entry_id, exception",
        [
            [3, NotFound],  # the entry is not accessible to user ID 1
            [4, NotFound],  # the entry is not in the database
        ],
    )
    def test_get_authorized_entry_invalid(
        self, authorized_entry_handler, authorized_entry_id, exception
    ):
        with pytest.raises(exception):
            authorized_entry_handler.get_entry(authorized_entry_id)

    @pytest.mark.parametrize(
        "criteria, reference_entry",
        [
            ["entry_criteria_x_single", db_reference[1]],
        ],
        indirect=["criteria"],
    )
    def test_find_statement(self, entry_handler, criteria, reference_entry):
        entry = entry_handler.find_entry(criteria=criteria)
        if reference_entry is None:
            assert entry is None
        else:
            self.assert_entry_matches(entry, reference_entry)

    @pytest.mark.parametrize(
        "criteria", ["entry_criteria_x_empty", None], indirect=True
    )
    def test_find_entry_none_exist(self, entry_handler, criteria):
        entry = entry_handler.find_entry(criteria)
        assert entry is None

    def test_find_non_unique_entry(self, entry_handler):
        criteria = QueryCriteria()
        criteria.add_match_filter(Entry, "user_id", 1)
        entry = entry_handler.find_entry(criteria=criteria, require_unique=False)
        self.assert_entry_matches(entry, self.db_reference[0])

    @pytest.mark.parametrize(
        "mapping",
        [
            {"x": 4, "y": "thirty", "user_id": 1},
            {"x": 5, "y": "thirty", "user_id": 1},
            {"x": 6, "y": "thirty", "user_id": 2},
        ],
    )
    def test_add_entry(self, entry_handler, mapping):
        entry = entry_handler.add_entry(**mapping)
        # Check that the entry object was properly created
        assert entry.y == "thirty"
        # Check that the entry was added to the database
        self.assert_number_of_matches(1, Entry.x, Entry.y == "thirty")

    @pytest.mark.parametrize(
        "mapping, exception",
        [
            [{"x": 4, "invalid_field": "Test", "user_id": 1}, TypeError],
            [{"x": 4, "user_id": 1}, IntegrityError],
        ],
    )
    def test_add_entry_invalid(self, entry_handler, mapping, exception):
        with pytest.raises(exception):
            entry_handler.add_entry(**mapping)

    @pytest.mark.parametrize(
        "mapping",
        [
            {"a": 4, "b": "four", "c": 1},
            {"a": 5, "b": "four", "c": 1},
            {"a": 4, "b": "four", "c": 2},
        ],
    )
    def test_add_authorized_entry(self, authorized_entry_handler, mapping):
        authorized_entry = authorized_entry_handler.add_entry(**mapping)
        # Check that the entry object was properly created
        assert authorized_entry.b == "four"
        # Check that the entry was added to the database
        self.assert_number_of_matches(1, AuthorizedEntry.b, AuthorizedEntry.b == "four")

    @pytest.mark.parametrize(
        "mapping, exception",
        [
            [{"a": 4, "invalid_field": "four", "c": 1}, TypeError],
            [{"a": 5, "b": "four"}, IntegrityError],
        ],
    )
    def test_add_authorized_entry_invalid(
        self, authorized_entry_handler, mapping, exception
    ):
        with pytest.raises(exception):
            authorized_entry = authorized_entry_handler.add_entry(**mapping)

    def test_add_authorized_entry_invalid_user(self, authorized_entry_handler):
        mapping = {
            "a": 4,
            "b": "four",
            "c": 3,  # foreign key mapping to an entry with user ID 2
        }
        # Ensure that user with ID 1 cannot add an entry linked to user ID 2
        self.assert_invalid_user_entry_add_fails(authorized_entry_handler, mapping)

    @pytest.mark.parametrize(
        "mapping",
        [
            {"y": "test", "user_id": 1},
            {"y": "test", "user_id": 2},  # not restricted by authorization
            {"y": "test"},
        ],
    )
    def test_update_entry(self, entry_handler, mapping):
        entry = entry_handler.update_entry(2, **mapping)
        # Check that the entry object was properly updated
        assert entry.y == "test"
        # Check that the entry was updated in the database
        self.assert_number_of_matches(1, Entry.x, Entry.y == "test")

    @pytest.mark.parametrize(
        "entry_id, mapping, exception",
        [
            # Invalid field
            [2, {"invalid_field": "test", "user_id": 1}, ValueError],
            # Nonexistent ID
            [4, {"y": "test", "user_id": 1}, NotFound],
        ],
    )
    def test_update_entry_invalid(self, entry_handler, entry_id, mapping, exception):
        with pytest.raises(exception):
            entry_handler.update_entry(entry_id, **mapping)

    @pytest.mark.parametrize(
        "mapping",
        [
            {"y": "test", "user_id": 1},
            {"y": "test", "user_id": 2},  # not restricted by authorization
            {"y": "test"},
        ],
    )
    def test_update_entry(self, entry_handler, mapping):
        entry = entry_handler.update_entry(2, **mapping)
        # Check that the entry object was properly updated
        assert entry.y == "test"
        # Check that the entry was updated in the database
        self.assert_number_of_matches(1, Entry.x, Entry.y == "test")

    @pytest.mark.parametrize(
        "authorized_entry_id, mapping, exception",
        [
            # Wrong entry user
            [3, {"b": "test", "c": 3}, NotFound],
            # Wrong entry user (trying to change to authorized user)
            [3, {"b": "test", "c": 2}, NotFound],
            # Invalid field
            [2, {"invalid_field": "test", "c": 1}, ValueError],
            # Nonexistent ID
            [4, {"b": "test", "c": 1}, NotFound],
        ],
    )
    def test_update_authorized_entry_invalid(
        self, authorized_entry_handler, authorized_entry_id, mapping, exception
    ):
        with pytest.raises(exception):
            authorized_entry_handler.update_entry(authorized_entry_id, **mapping)

    @pytest.mark.parametrize("entry_id", [2, 3])
    def test_delete_entry(self, entry_handler, entry_id):
        self.assert_entry_deletion_succeeds(entry_handler, entry_id)
        # Check that any cascading entries were deleted
        self.assert_number_of_matches(
            0, AuthorizedEntry.a, AuthorizedEntry.c == entry_id
        )

    @pytest.mark.parametrize(
        "entry_id, exception",
        [
            [4, NotFound],  # should not be able to delete nonexistent entries
        ],
    )
    def test_delete_entry_invalid(self, entry_handler, entry_id, exception):
        with pytest.raises(exception):
            entry_handler.delete_entry(entry_id)

    @pytest.mark.parametrize("entry_id", [1, 2])
    def test_delete_authorized_entry(self, authorized_entry_handler, entry_id):
        self.assert_entry_deletion_succeeds(authorized_entry_handler, entry_id)
        # Check that any cascading entries were deleted
        self.assert_number_of_matches(
            0, AlternateAuthorizedEntry.p, AlternateAuthorizedEntry.q == entry_id
        )

    @pytest.mark.parametrize(
        "authorized_entry_id, exception",
        [
            [3, NotFound],  # should not be able to delete other user entries
            [4, NotFound],  # should not be able to delete nonexistent entries
        ],
    )
    def test_delete_authorized_entry_invalid(
        self, authorized_entry_handler, authorized_entry_id, exception
    ):
        with pytest.raises(exception):
            authorized_entry_handler.delete_entry(authorized_entry_id)


class AlternateAuthorizedEntryViewHandler(
    DatabaseViewHandler,
    model=AlternateAuthorizedEntry,
    model_view=AlternateAuthorizedEntryView,
):
    """A minimal database view handler for testing."""


@pytest.fixture
def view_handler(client_context):
    with mocked_user(user_id=1):
        yield AlternateAuthorizedEntryViewHandler


class TestDatabaseViewHandler(TestHandler):
    # Reference only includes authorized entries accessible to user ID 1
    db_reference = [
        AlternateAuthorizedEntryView(p=1, q=1, r=2),
        AlternateAuthorizedEntryView(p=2, q=2, r=4),
    ]

    def test_initialization(self, view_handler):
        assert view_handler.model == AlternateAuthorizedEntry
        assert view_handler.table.name == "alt_authorized_entries"
        assert view_handler.table_view.name == "alt_authorized_entries_view"
        assert view_handler.user_id == 1
