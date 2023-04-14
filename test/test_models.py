"""Tests for the specialized authorization models."""
import pytest

from authanor.models import AuthorizedAccessMixin, Model


class TestAuthorizedModels:
    def test_invalid_authorized_model(self):
        # Define an "authorized access" class to test authorization
        class AuthorizedModel(AuthorizedAccessMixin, Model):
            # Pass a valid table name
            __tablename__ = "test"

        # Test that the model cannot make a selection based on the user
        authorized_model = AuthorizedModel()
        with pytest.raises(AttributeError):
            authorized_model.select_for_user()
