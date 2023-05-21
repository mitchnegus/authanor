"""Tests for utility functions."""
from contextlib import nullcontext as does_not_raise

import pytest
from sqlalchemy import select
from sqlalchemy.sql.expression import func

from authanor.database.utils import db_transaction, validate_sort_order
from authanor.testing.helpers import transaction_lifetime

from test_helpers import Entry


@pytest.mark.parametrize(
    "sort_order, expectation",
    [
        ["ASC", does_not_raise()],
        ["DESC", does_not_raise()],
        ["test", pytest.raises(ValueError)],
    ],
)
def test_validate_sort_order(sort_order, expectation):
    with expectation:
        validate_sort_order(sort_order)


@transaction_lifetime
def test_transaction_decorator(client_context, app):
    # Define a function that uses the transaction generator to commit an action
    @db_transaction
    def execute_database_transaction(app, x, y):
        entry = Entry(x=x, y=y, user_id=1)
        app.db.session.add(entry)

    x, y = 5, "fifty"
    execute_database_transaction(app, x, y)
    # Ensure that the transaction was actually added
    query = select(func.count(Entry.x)).where(Entry.y == y)
    assert app.db.session.execute(query).scalar() == 1
