from unittest.mock import Mock, patch

import pytest
from flask import Flask
from sqlalchemy import create_engine

from authanor.database import SQLAlchemy as _SQLAlchemy
from authanor.test.helpers import AppTestManager

from .helpers import AuthorizedEntry, Entry


class SQLAlchemy(_SQLAlchemy):
    def initialize(self, app):
        """Initialize (and prepopulate) the database for testing."""
        super().initialize(app)
        with app.db.session.begin():
            entries = [
                Entry(x=1, y="ten", user_id=1),
                Entry(x=2, y="eleven", user_id=1),
                Entry(x=3, y="twenty", user_id=2),
            ]
            authorized_entries = [
                AuthorizedEntry(a=1, b="one", c=1),
                AuthorizedEntry(a=2, b="two", c=1),
                AuthorizedEntry(a=3, b="three", c=3),
            ]
            app.db.session.add_all(entries + authorized_entries)


def create_test_app(test_config):
    # Create and configure the test app
    app = Flask("test")
    app.config.from_object(test_config)
    init_app(app)
    return app


@SQLAlchemy.interface_selector(interface_instance=None)
def init_app(app):
    # Initialize the app
    # * The decorator performs all necessary actions in this minimal test example
    pass


# Instantiate the app manager to determine the correct app (persistent/ephemeral)
app_manager = AppTestManager(factory=create_test_app)


@pytest.fixture
def app():
    yield app_manager.get_app()


@pytest.fixture
def client(app):
    yield app.test_client()


@pytest.fixture
def client_context(client):
    with client:
        # Context variables (e.g., `g`) may be accessed only after response
        client.get("/")
        yield
