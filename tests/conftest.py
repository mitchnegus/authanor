from unittest.mock import Mock, patch

import pytest
from flask import Flask
from sqlalchemy import Integer, String, create_engine
from sqlalchemy.orm import mapped_column

from authanor.database import SQLAlchemy
from authanor.models import AuthorizedAccessMixin, Model
from authanor.test.helpers import AppTestManager


class Entry(Model):
    __tablename__ = "entries"
    # Columns
    x = mapped_column(Integer, primary_key=True)
    y = mapped_column(String, nullable=False)
    user_id = mapped_column(Integer, nullable=False)


class AuthorizedEntry(AuthorizedAccessMixin, Model):
    __tablename__ = "authorized_entries"
    _user_id_join_chain = (Entry,)
    # Columns
    a = mapped_column(Integer, primary_key=True)
    b = mapped_column(String, nullable=False)


@pytest.fixture
def entry_model_type():
    return Entry


@pytest.fixture
def authorized_entry_model_type():
    return AuthorizedEntry


def create_test_app(test_config):
    # Create and configure the test app
    app = Flask("test")
    app.config.from_object(test_config)
    # Set up the test database
    app.db = SQLAlchemy()
    app.db.setup_engine(test_config.DATABASE)
    app.db.create_tables()
    return app


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
