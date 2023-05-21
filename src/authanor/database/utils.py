"""
Tools for connecting to and working with the SQLite database.
"""
from functools import wraps

from flask import current_app


def db_transaction(func):
    """A decorator denoting the wrapped function as a database transaction."""

    @wraps(func)
    def wrapper(*args, **kwargs):
        with current_app.db.session.begin():
            return func(*args, **kwargs)

    return wrapper


def validate_sort_order(sort_order):
    """
    Ensure that a valid sort order was provided.

    Parameters
    ----------
    sort_order : str
        The order, ascending or descending, that should be used when
        sorting the returned values from the database query. The order
        must be either 'ASC' or 'DESC'.
    """
    if sort_order not in ("ASC", "DESC"):
        raise ValueError(
            f"Provide a valid sort order—either 'ASC' or 'DESC', not '{sort_order}'."
        )
