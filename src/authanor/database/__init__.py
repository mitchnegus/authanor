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
    default_interface = None

    def __init__(self, echo_engine=False):
        self.engine = None
        self.scoped_session = None
        self.echo_engine = echo_engine

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

    def setup_engine(self, db_path, echo_engine=None):
        """
        Setup the database engine, a session factory, and metadata.

        Parameters
        ----------
        db_path : os.PathLike
            The path to the local database.
        """
        echo_engine = self.echo_engine if echo_engine is None else echo_engine
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
    def create_default_interface(cls, *args, **kwargs):
        """Create a default interface for the app."""
        cls.default_interface = cls(*args, **kwargs)

    @classmethod
    def interface_selector(cls, init_app_func):
        """
        A decorator to choose the database interface.

        This decorator wraps an app initialization function to determine
        whether a new interface should be created (e.g., during testing)
        or an existing (default) interface previously instantiated by
        the application should be used instead. This selector assumes
        that the path to the local database instance will be provided by
        the app's configuration.

        Parameters
        ----------
        init_app_func : callable
            A function to initialize the app. Usually this function is
            called from within the Flask app factory function.

        Returns
        -------
        decorator : func
            The wrapper function that sets the database interface.
        """

        @functools.wraps(init_app_func)
        def wrapper(app):
            # Prepare database access with SQLAlchemy:
            # - Use the `app.db` attribute like the `app.extensions` dict
            #   (but not actually that dict because this is not an extension)
            if not app.testing:
                if not cls.default_interface:
                    raise RuntimeError(
                        "A default database interface has not yet been defined. "
                        "Define a default interface for all apps running in "
                        "production or development mode."
                    )
                app.db = cls.default_interface
            else:
                app.db = cls(
                    *app.config["DATABASE_INTERFACE_ARGS"],
                    **app.config["DATABASE_INTERFACE_KWARGS"],
                )
            app.db.setup_engine(db_path=app.config["DATABASE"])
            init_app_func(app)
            # Establish behavior for closing the database
            app.teardown_appcontext(app.db.close)
            # If testing, the database still needs to be initialized/prepopulated
            # (otherwise, database initialization is typically executed via the CLI)
            if app.testing:
                app.db.initialize(app)
        return wrapper


@event.listens_for(Engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()
