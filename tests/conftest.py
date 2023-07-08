from unittest.mock import Mock, patch

import pytest
from flask import Flask
from fuisce.database import SQLAlchemy
from fuisce.testing import AppTestManager

from testing_helpers import AlternateAuthorizedEntry, AuthorizedEntry, Entry


class AuthanorAppTestManager(AppTestManager):
    """A test manager for the Authanor app."""

    def prepare_test_database(self, db):
        with db.session.begin():
            entries = [
                Entry(x=1, y="ten", user_id=1),
                Entry(x=2, y="eleven", user_id=1),
                Entry(x=3, y="twelve", user_id=1),
                Entry(x=4, y="twenty", user_id=2),
                AuthorizedEntry(a=1, b="one", c=1),
                AuthorizedEntry(a=2, b="two", c=1),
                AuthorizedEntry(a=3, b="three", c=4),
                AlternateAuthorizedEntry(p=1, q=1),
                AlternateAuthorizedEntry(p=2, q=2),
                AlternateAuthorizedEntry(p=3, q=2),
                AlternateAuthorizedEntry(p=4, q=3),
            ]
            db.session.add_all(entries)


def create_test_app(test_config):
    # Create and configure the test app
    app = Flask("test")
    app.config.from_object(test_config)
    init_app(app)
    return app


@SQLAlchemy.interface_selector
def init_app(app):
    # Initialize the app
    # * The decorator performs all necessary actions in this minimal test example
    pass


# Instantiate the app manager to determine the correct app (persistent/ephemeral)
app_manager = AuthanorAppTestManager(factory=create_test_app)


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
