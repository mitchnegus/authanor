"""Tests for the specialized authorization models."""
from unittest.mock import Mock, call, patch

import pytest

from authanor.models import AuthorizedAccessMixin, Model


class TestModels:
    def test_model_initialization(self, entry_model_type):
        mapping = {
            "x": 1,
            "y": "test1",
            "user_id": 1,
        }
        model = entry_model_type(**mapping)
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
    def test_model_representation(
        self, entry_model_type, mapping, expected_repr_string
    ):
        entry = entry_model_type(**mapping)
        assert repr(entry) == expected_repr_string


class TestAuthorizedModels:
    def test_user_id_join_chain(self, authorized_entry_model_type, entry_model_type):
        assert authorized_entry_model_type.user_id_model == entry_model_type

    def test_model_is_user_id_model(self, authorized_entry_model_type):
        with patch.object(authorized_entry_model_type, "_user_id_join_chain", new=()):
            assert (
                authorized_entry_model_type.user_id_model is authorized_entry_model_type
            )

    @patch("authanor.models.select")
    @patch("authanor.models.g")
    def test_select_for_user(
        self,
        mock_global_namespace,
        mock_select_method,
        client_context,
        authorized_entry_model_type,
    ):
        authorized_entry_model_type.select_for_user()
        mock_select_method.assert_called_once_with(authorized_entry_model_type)

    @patch("authanor.models.select")
    @patch("authanor.models.g")
    def test_select_specified_for_user(
        self,
        mock_global_namespace,
        mock_select_method,
        client_context,
        authorized_entry_model_type,
    ):
        mock_args = [Mock(), Mock(), Mock()]
        authorized_entry_model_type.select_for_user(*mock_args)
        mock_select_method.assert_called_once_with(*mock_args)

    @patch("authanor.models.AuthorizedAccessMixin._join_user")
    @patch("authanor.models.select")
    @patch("authanor.models.g")
    def test_select_for_user_guaranteed_joins(
        self,
        mock_global_namespace,
        mock_select_method,
        mock_join_user_method,
        client_context,
        authorized_entry_model_type,
    ):
        # Mock a `Select` object (to be iteratively mutated)
        mock_select = Mock()
        mock_join_user_method.return_value = mock_select
        mock_select.join.return_value = mock_select
        # Issue the select statement relying on the mocked objects
        mock_joins = [Mock(), Mock(), Mock()]
        authorized_entry_model_type.select_for_user(guaranteed_joins=mock_joins)
        mock_select.join.assert_has_calls([call(_) for _ in mock_joins])
        assert mock_select.join.call_count == len(mock_joins)

    @patch("authanor.models.AuthorizedAccessMixin.user_id_model", new=None)
    @patch("authanor.models.g")
    def test_invalid_authorized_model(
        self, mock_global_namespace, client_context, authorized_entry_model_type
    ):
        # Test that the model cannot make a selection based on the user
        with pytest.raises(AttributeError):
            authorized_entry_model_type.select_for_user()
