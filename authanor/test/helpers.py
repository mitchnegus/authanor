"""
Helper tools to improve testing of authorized database interactions.
"""
import functools
import os
import tempfile
from collections import namedtuple
from contextlib import contextmanager

import pytest


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
    def wrapped_test_function(*args, **kwargs):
        test_function(*args, **kwargs)

    return wrapped_test_function


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
