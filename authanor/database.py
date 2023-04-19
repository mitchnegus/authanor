"""
Tools for connecting to and working with the SQLite database.
"""
from sqlalchemy import MetaData, create_engine
from sqlalchemy.orm import scoped_session, sessionmaker

from .models import Model

DIALECT = "sqlite"
DBAPI = "pysqlite"


class SQLAlchemy:
    """Store SQLAlchemy database objects."""

    _base = Model

    def __init__(self, db_path=None):
        self.engine = None
        self.metadata = None
        self.scoped_session = None

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
        # Add metadata
        self.metadata = MetaData()

    def create_tables(self):
        """Create tables from the model metadata."""
        self.metadata.create_all(self.engine)


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
        raise ValueError("Provide a valid sort order.")
