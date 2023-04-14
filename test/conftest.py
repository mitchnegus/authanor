import pytest
from sqlalchemy import create_engine, Integer, String
from sqlalchemy.orm import mapped_column

from authanor.models import Model


class TestModel(Model):
    __tablename__ = "test"
    # Columns
    x = mapped_column(Integer, primary_key=True)
    y = mapped_column(String, nullable=False)


@pytest.fixture(autouse=True)
def database():
    engine = create_engine("sqlite://", echo=True)
    Model.metadata.create_all(engine)
