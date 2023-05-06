"""Tests for the specialized authorization models."""
from unittest.mock import Mock, call, patch

import pytest

from authanor.database.models import AuthorizedAccessMixin, Model

from test_helpers import AuthorizedEntry, Entry


class TestModels:
    def test_model_initialization(self):
        mapping = {
            "x": 1,
            "y": "test1",
            "user_id": 1,
        }
        model = Entry(**mapping)
        for field in mapping:
            assert getattr(model, field) == mapping[field]

    @pytest.mark.parametrize(
        "mapping, expected_repr_string",
        [
            [
                {"x": 2, "y": "test2", "user_id": 1},
                "Entry(x=2, y='test2', user_id=1)",
            ],
            [
                {"x": 2, "y": "test2 and some other long text", "user_id": 1},
                "Entry(x=2, y='test2 and some other long...', user_id=1)",
            ],
        ],
    )
    def test_model_representation(self, mapping, expected_repr_string):
        entry = Entry(**mapping)
        assert repr(entry) == expected_repr_string


class TestAuthorizedModels:
    def test_user_id_join_chain(self):
        assert AuthorizedEntry.user_id_model is Entry

    def test_missing_user_id_join_chain(self):
        class InvalidAuthorizedEntry(AuthorizedEntry):
            _user_id_join_chain = ()

        assert InvalidAuthorizedEntry.user_id_model is InvalidAuthorizedEntry

    def test_model_is_user_id_model(self):
        with patch.object(AuthorizedEntry, "_user_id_join_chain", new=()):
            assert AuthorizedEntry.user_id_model is Entry

    @patch("authanor.database.models.select")
    @patch("authanor.database.models.g")
    def test_select_for_user(
        self,
        mock_global_namespace,
        mock_select_method,
        client_context,
    ):
        AuthorizedEntry.select_for_user()
        mock_select_method.assert_called_once_with(AuthorizedEntry)

    @patch("authanor.database.models.select")
    @patch("authanor.database.models.g")
    def test_select_specified_for_user(
        self,
        mock_global_namespace,
        mock_select_method,
        client_context,
    ):
        mock_args = [Mock(), Mock(), Mock()]
        AuthorizedEntry.select_for_user(*mock_args)
        mock_select_method.assert_called_once_with(*mock_args)

    @patch("authanor.database.models.AuthorizedAccessMixin._join_user")
    @patch("authanor.database.models.select")
    @patch("authanor.database.models.g")
    def test_select_for_user_guaranteed_joins(
        self,
        mock_global_namespace,
        mock_select_method,
        mock_join_user_method,
        client_context,
    ):
        # Mock a `Select` object (to be iteratively mutated)
        mock_select = Mock()
        mock_join_user_method.return_value = mock_select
        mock_select.join.return_value = mock_select
        # Issue the select statement relying on the mocked objects
        mock_joins = [Mock(), Mock(), Mock()]
        AuthorizedEntry.select_for_user(guaranteed_joins=mock_joins)
        mock_select.join.assert_has_calls([call(_) for _ in mock_joins])
        assert mock_select.join.call_count == len(mock_joins)

    @patch("authanor.database.models.g")
    def test_invalid_authorized_model(self, mock_global_namespace, client_context):
        # Test that the model cannot make a selection based on the user
        with patch.object(AuthorizedEntry, "user_id_model", new=None):
            with pytest.raises(AttributeError):
                AuthorizedEntry.select_for_user()
