"""
Helper tools to improve testing of authorized database interactions.
"""
import textwrap
import functools
import os
import tempfile
from collections import namedtuple
from contextlib import contextmanager
from pprint import pformat

import pytest
from sqlalchemy import inspect, select
from sqlalchemy.sql.expression import func
from werkzeug.exceptions import NotFound


registry = {"app_manager": None}


class DefaultTestingConfig:
    """A Flask configuration designed for testing."""
    TESTING = True
    SECRET_KEY = "testing key"

    def __init__(self, db_path=None):
        self.DATABASE = db_path


class AppTestManager:
    """
    An object for managing apps during testing.

    Flask tests require access to an app, and this app provides access
    to the database. To avoid recreating the database on every test (and
    thus substantially improve test performance times), it is convenient
    to persist the app and database throughout the duration of testing.
    However, tests that consist of complete SQLAlchemy transactions
    which alter the database (e.g., additions, updates, deletions;
    operations that include a commit) would change this persistent
    database version and impact subsequent tests. Since simply rolling
    back the changes is insufficient to restore the database, this
    object manages which app (and database) are used for a transaction.
    The current app options are either
        (1) A persistent app, which survives through the entire test
            process and provides quick database access; or
        (2) An ephemeral app, which is designed to survive through only
            one single test.

    To enable switching between the two types of apps, this class relies
    on two Pytest fixtures (`app_context` and `app_transaction_context`)
    to control the scope of the two apps. The `app_context` fixture is
    created just once for the session and is then automatically used in
    all tests. On the other hand, the `app_transaction_context` fixture
    may be manually included in any test, which causes an ephemeral app
    to be created (and then used) only for that one test. To avoid
    cluttering test signatures, the `transaction_lifetime` decorator
    helper is provided to signal that a test should use the ephemeral
    app rather than calling the `app_transaction_context` fixture
    directly.
    """

    persistent_app = None
    ephemeral_app = None

    def __init__(self, factory):
        self.app_factory = factory
        registry["app_manager"] = self

    def get_app(self):
        if self.ephemeral_app:
            app = self.ephemeral_app
        else:
            app = self.persistent_app
        return app

    def generate_app(self, test_database_path, *args, **kwargs):
        # Create a testing app
        test_config = self.prepare_test_config(test_database_path, *args, **kwargs)
        app = self.app_factory(test_config)
        self.setup_test_database(app)
        return app

    def persistent_context(self):
        return self.app_test_context("persistent_app")

    def ephemeral_context(self):
        return self.app_test_context("ephemeral_app")

    @contextmanager
    def app_test_context(self, app_name, *args, **kwargs):
        """
        Create a testing context for an app.

        Given the app name (either "ephemeral_app" or "persistent_app"),
        this context manager defines a context for that app, including
        the creation of a temporary database to be used by that version
        of the test app. Multiple test contexts may be generated and
        associated with the `AppManager` to enable access to different
        apps depending on the test.
        """
        with self._database_test_context() as test_db:
            app = self.generate_app(test_db.path, *args, **kwargs)
            setattr(self, app_name, app)
            yield
            setattr(self, app_name, None)

    @staticmethod
    @contextmanager
    def _database_test_context():
        """
        Create a temporary file for the database.

        This context manager creates a temporary file that is used for the
        testing database. The temporary file persists as long as the context
        survives, and the temporarykjj file is removed after the context
        lifetime is completed.
        """
        db_fd, db_path = tempfile.mkstemp()
        yield namedtuple("TemporaryFile", ["fd", "path"])(db_fd, db_path)
        # After function execution, close the file and remove it
        os.close(db_fd)
        os.unlink(db_path)

    @staticmethod
    def prepare_test_config(test_db_path, *args, **kwargs):
        """Prepare a configuration object for the app. It must define a database."""
        return DefaultTestingConfig(test_db_path)

    @staticmethod
    def setup_test_database(app):
        pass


def transaction_lifetime(test_function):
    """
    Create a decorator to leverage an ephemeral app.

    While many tests just check elements in the database, and so can
    share a persistent app object for performance reasons. However, some
    transactions must update (and commit to) the database to be
    successful. For these cases, this decorator provides access to an
    app object with a lifetime of only this one transaction. That new
    app is entirely separate from the persistent app, and so generates
    an entirely new instance of the test database that exists only for
    the lifetime of the test being decorated.

    Parameters
    ----------
    test_function : callable
        The test function to be decorated which will use a new app with
        a lifetime of just this test (one database transaction).

    Returns
    -------
    wrapped_test_function : callable
        The wrapped test.
    """
    @pytest.mark.usefixtures("app_transaction_context")
    @functools.wraps(test_function)
    def wrapper(*args, **kwargs):
        test_function(*args, **kwargs)
    return wrapper


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
    def assertEntryMatches(entry, reference):
        assert isinstance(entry, type(reference))
        for column in inspect(type(entry)).columns:
            field = column.name
            assert getattr(entry, field) == getattr(reference, field), (
                "A field in the entry does not match the reference"
                f"\n\treference: {reference}"
                f"\n\t    entry: {entry}"
            )

    @classmethod
    def assertEntriesMatch(cls, entries, references, order=False):
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
            cls.assertEntryMatches(entry, reference)

    def assertNumberOfMatches(self, number, field, *criteria):
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
        self.assertNumberOfMatches(
            entry_count, handler.model.primary_key_field
        )

    def assert_entry_deletion_succeeds(self, handler, entry_id):
        handler.delete_entry(entry_id)
        # Check that the entry was deleted
        self.assertNumberOfMatches(
            0,
            handler.model.primary_key_field,
            handler.model.primary_key_field == entry_id
        )


def pytest_generate_tests(metafunc):
    """
    Control test generation.

    This function overrides the built-in Pytest function to explicitly
    control test generation. Here, controlling test generation is
    required to alter the order of the `metafunc.fixturenames`
    attribute. The fixtures defined in that list are called (in order)
    when setting up a test function; however, for this app's tests to
    perform optimally, the `app_transaction_context` must be the very
    first fixture called so that the proper testing context is used.
    """
    priority_fixture = "app_transaction_context"
    if priority_fixture in metafunc.fixturenames:
        metafunc.fixturenames.remove(priority_fixture)
        metafunc.fixturenames.insert(0, priority_fixture)


@pytest.fixture(scope="session", autouse=True)
def app_context():
    with registry["app_manager"].persistent_context():
        yield


@pytest.fixture
def app_transaction_context():
    with registry["app_manager"].ephemeral_context():
        yield
