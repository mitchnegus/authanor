"""
Tools for connecting to and working with the SQLite database.
"""
import functools

from flask import current_app
from sqlalchemy import MetaData, create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import scoped_session, sessionmaker

from .models import Model
from .utils import db_transaction

DIALECT = "sqlite"
DBAPI = "pysqlite"


class SQLAlchemy:
    """Store an interface to SQLAlchemy database objects."""

    _base = Model

    def __init__(self, db_path=None):
        self.engine = None
        self.scoped_session = None

    @property
    def metadata(self):
        return self._base.metadata

    @property
    def tables(self):
        return self.metadata.tables

    @property
    def session(self):
        # Returns the current `Session` object
        return self.scoped_session()

    def setup_engine(self, db_path, echo_engine=False):
        """Setup the database engine, a session factory, and metadata."""
        # Create the engine using the custom database URL
        db_url = f"{DIALECT}+{DBAPI}:///{db_path}"
        self.engine = create_engine(db_url, echo=echo_engine)
        # Use a session factory to generate sessions
        session_factory = sessionmaker(
            bind=self.engine,
            autoflush=False,
            future=True,
        )
        self.scoped_session = scoped_session(session_factory)
        self._base.query = self.scoped_session.query_property()

    def initialize(self, app):
        """
        Initialize the database.

        Initialize the database, possibly using any additional arguments
        necessary. This method is designed to be extended by
        app-specific interfaces with customized initialization
        procedures.

        Parameters
        ----------
        app : flask.Flask
            The app object, which may pass initialization parameters via
            its configuration.
        """
        self.create_tables()

    def create_tables(self):
        """Create tables from the model metadata."""
        self.metadata.create_all(bind=self.engine)

    def close(self, exception=None):
        """Close the database if it is open."""
        if self.scoped_session is not None:
            self.scoped_session.remove()

    @classmethod
    def interface_selector(cls, interface_instance):
        """
        A decorator to choose between the database interface.

        This decorator wraps an app initialization function to determine
        whether a new interface should be created (e.g., during testing)
        or an existing interface previously instantiated by the
        application should be used instead.

        Parameters
        ----------
        interface_instance : authanor.database.SQLAlchemy
            An existing database interface instance to potentially use.

        Returns
        -------
        decorator : func
            The wrapper function that sets the database interface.
        """

        def _inner_decorator(init_app_func):
            @functools.wraps(init_app_func)
            def wrapper(app):
                # Prepare database access with SQLAlchemy
                #   - Use the `app.db` attribute like the `app.extensions` dict
                #     (but not actually that dict because this is not an extension)
                app.db = cls() if app.testing else interface_instance
                app.db.setup_engine(db_path=app.config["DATABASE"])
                init_app_func(app)
                # Establish behavior for closing the database
                app.teardown_appcontext(app.db.close)
                # If testing, the database still needs to be initialized/prepopulated
                if app.testing:
                    app.db.initialize(app)

            return wrapper

        return _inner_decorator


@event.listens_for(Engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()
