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

from ..helpers import AuthorizedEntry, Entry


class EntryHandler(DatabaseHandler, model=Entry):
    """A minimal database handler for testing."""


class AuthorizedEntryHandler(DatabaseHandler, model=AuthorizedEntry):
    """A minimal database handler for testing."""


@contextmanager
def mocked_user(user_id):
    with patch("authanor.database.handler.g") as mock_global_namespace:
        with patch("authanor.database.models.g", new=mock_global_namespace):
            mock_global_namespace.user = Mock(id=1)
            yield


@pytest.fixture
def entry_handler(client_context):
    with mocked_user(user_id=1):
        yield EntryHandler


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
        assert entry_handler.table == "entries"
        assert entry_handler.user_id == 1
