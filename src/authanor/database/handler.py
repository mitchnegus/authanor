"""
A database handler for facilitating interactions with the SQLite database.
"""
import functools
from abc import ABCMeta
from collections import UserList

from flask import current_app, g
from sqlalchemy import select
from sqlalchemy.exc import ArgumentError, NoResultFound
from werkzeug.exceptions import abort

from .models import AuthorizedAccessMixin
from .utils import validate_sort_order


class DatabaseHandlerMeta(ABCMeta):
    """
    A metaclass defining a universal API for database handlers.

    All database handlers provide access to the database focusing
    primarily on access to a specific SQLAlchemy ORM model. Although
    the model and many of the associated methods vary depending on the
    handler and the model's role, the overall pattern remains relatively
    consistent across handlers. Because of that, this metaclass
    prescribes those common behaviors. When a model-specific handler is
    defined, a model must be provided as a keyword argument to the
    metaclass. This model is set on that model-specific class, and is
    accessed using the corresponding property defined by this metaclass.
    """

    def __new__(mcls, name, bases, namespace, **kwargs):
        namespace.setdefault("model", kwargs.get("model"))
        return super().__new__(mcls, name, bases, namespace)

    @property
    def _db(cls):
        return current_app.db

    @property
    def user_id(cls):
        return g.user.id

    @property
    def model(cls):
        return cls._get_required_attribute_data_descriptor("model")

    @property
    def table(cls):
        return cls.model.__table__

    def _get_required_attribute_data_descriptor(cls, name):
        # The named property/attribute is a data descriptor, so standard overrides are
        # not permitted; instead, the metaclass property must reference the true
        # class's dictionary of values to get the overridden attribute
        value = cls.__dict__.get(name)
        if value:
            return value
        # The handler subclass must have given the attribute a value to be valid
        raise NotImplementedError(f"Define a value for '{name}' in this subclass.")


class DatabaseViewHandlerMeta(DatabaseHandlerMeta):
    """
    A metaclass defining a universal API for database view handlers.

    Similar to the `DatabaseHandlerMeta`, this metasubclass defines a
    consistent set of behaviors for database handlers that focus on a
    model based on a database view (rather than a native database
    component). Since the ORM model views managed by a handler each have
    a corresponding model (based on a native database component), that
    component and the view are specified when defining a model-specific
    handler.
    """

    def __new__(mcls, name, bases, namespace, **kwargs):
        namespace.setdefault("_model", kwargs.get("model"))
        namespace.setdefault("_model_view", kwargs.get("model_view"))
        return super().__new__(mcls, name, bases, namespace)

    @property
    def _model(cls):
        return cls._get_required_attribute_data_descriptor("_model")

    @property
    def _model_view(cls):
        return cls._get_required_attribute_data_descriptor("_model_view")

    @property
    def model(cls):
        return cls._model_view if cls._view_context else cls._model

    @property
    def table(cls):
        return cls._model.__table__

    @property
    def table_view(cls):
        return cls._model_view.__table__


class QueryCriteria(UserList):
    """
    A helper object for constructing queries using a database handler.
    """

    def __init__(self):
        super().__init__()
        self.discriminators = []

    def add_match_filter(self, model, field, values):
        """
        Add a filter to the query to select only matching entries.

        Parameters
        ----------
        model : database.models.Model
            The ORM model representing the table to to be filtered.
        field : str
            The name of the field which is the subject of the filter.
        values :
            A list of values (or a singular value) that will applied
            as the matching criteria for the field.
        """
        # Build a filter based on any given value(s)
        if values is not None:
            try:
                criterion = getattr(model, field).in_(values)
            except ArgumentError:
                criterion = getattr(model, field) == values
            self.data.append(criterion)
            self.discriminators.append(model)

    def append(self, item):
        raise RuntimeError(
            "The `QueryCriteria` object can not be appended to directly. Use a helper "
            "method (e.g., `add_match_filter`) instead."
        )


class DatabaseHandlerMixin:
    """
    A mixin providing the functionality of a database handler.

    Note
    ----
    Tools relying on the database handler functionality (e.g., both the
    `DatabaseHandler` and the `DatabaseViewHandler`) may have different
    metaclasses. This mixin allows the functionality of a database
    handler to be shared by any objects that implement the database
    handler interface.
    """

    _initialize_criteria_list = QueryCriteria

    @classmethod
    def _build_select_query(cls, **kwargs):
        # Query entries for the authorized user (or fall back to SQLAlchemy `select`)
        select_method = getattr(cls.model, "select_for_user", select)
        query = select_method(cls.model, **kwargs)
        return query

    @classmethod
    def _customize_entries_query(cls, query, criteria, column_orders):
        """
        Customize a query to retrieve entries from the database.

        Parameters
        ----------
        query : sqlalchemy.sql.expression.Select
            The query to be customized.
        criteria : QueryCriteria
            Additional criteria to use when applying filters to the
            query. (Any filters with a value of `None` will be ignored.)
        column_orders : dict
            A mapping between columns and the sorting order to
            apply to those columns (e.g., 'ASC' or 'DESC'). Columns will
            be sorted first to last.

        Returns
        -------
        query : sqlalchemy.sql.expression.Select
            The customized (sorted, filtered, etc.) query.

        Note
        ----
        As an implementation detail, the query returned by this method
        defined in the lowest level subclass should always be the final
        query executed by the current `Session` object in the
        `get_entries` method.
        """
        column_orders = column_orders if column_orders else {}
        query = cls._sort_query(query, column_orders)
        return cls._filter_entries(query, criteria)

    @staticmethod
    def _filter_entries(query, criteria):
        """Apply filters to a query based on the given criteria."""
        if criteria:
            query = query.filter(*criteria)
        return query

    @classmethod
    def _execute_query(cls, query):
        return cls._db.session.execute(query)

    @classmethod
    def _sort_query(cls, query, column_orders):
        """
        Sort a query on the given column(s).

        Parameters
        ----------
        query : sqlalchemy.sql.expression.Select
            The query to be sorted.
        column_orders :
            A mapping of pairs consisting of a table column key and a
            string value describing the sorting order ('ASC' or 'DESC')
            for the column.
        """
        for column, sort_order in column_orders.items():
            if sort_order:
                validate_sort_order(sort_order)
                if sort_order == "DESC":
                    order_column = column.desc()
                elif sort_order == "ASC":
                    order_column = column.asc()
                query = query.order_by(order_column)
        return query

    @classmethod
    def get_entries(cls, entry_ids=None, criteria=None, column_orders=None, **kwargs):
        """
        Retrieve a set of entries from the database.

        Executes a simple query to select the table entries from
        the database which match the given filters.

        Parameters
        ----------
        entry_ids : list
            A set of primary keys (IDs) to be found.
        criteria : QueryCriteria
            Additional criteria to use when applying filters to the
            query. (Any filters with a value of `None` will be ignored.)
        column_orders : dict
            A mapping between column names and the sorting order to
            apply to those columns (e.g., 'ASC' or 'DESC'). Columns will
            be sorted first to last.
        **kwargs :
            Keyword arguments that may be defined for specific handler
            subclasses.

        Returns
        -------
        entries : list of database.models.Model
            Models containing matching entries from the database.
        """
        # Prepare the criteria by merging IDs with other criteria
        criteria = criteria if criteria else QueryCriteria()
        criteria.add_match_filter(cls.model, "primary_key_field", entry_ids)
        # Query the database
        query = cls._build_select_query(**kwargs)
        query = cls._customize_entries_query(query, criteria, column_orders)
        entries = cls._execute_query(query).scalars()
        return entries

    @classmethod
    def find_entry(cls, criteria=None, column_orders=None, require_unique=True):
        """
        Find an entry using uniquely identifying characteristics.

        Parameters
        ----------
        criteria : QueryCriteria
            Criteria to use when applying filters to the query. (If all
            criteria are `None`, the returned entry will be `None`.)
        column_orders : dict
            A mapping between column names and the sorting order to
            apply to those columns (e.g., 'ASC' or 'DESC'). Columns will
            be sorted first to last.
        require_unique : bool
            A flag indicating whether a found entry must be the one and
            only entry matching the criteria. The default is `True`, and
            if an entry is not the only one matching the criteria, an
            error is raised.

        Returns
        -------
        entry : database.models.Model
            A model containing a matching entry from the database.
        """
        if criteria:
            # Query entries from the authorized user
            query = cls._build_select_query()
            query = cls._customize_entries_query(query, criteria, column_orders)
            results = cls._execute_query(query)
            entry = results.scalar_one_or_none() if require_unique else results.scalar()
            return entry
        return None

    @classmethod
    def get_entry(cls, entry_id):
        """
        Retrieve a single entry from the database.

        Executes a simple query from the database to get a single entry
        by its primary key (most often its ID).

        Parameters
        ----------
        entry_id : int
            The primary key (ID) of the entry to be found.

        Returns
        -------
        entry : database.models.Model
            A model containing a matching entry from the database.
        """
        criteria = QueryCriteria()
        criteria.add_match_filter(cls.model, "primary_key_field", entry_id)
        query = cls._build_select_query().where(*criteria)
        try:
            entry = cls._execute_query(query).scalar_one()
        except NoResultFound:
            abort_msg = (
                f"The entry with ID {entry_id} does not exist for the current user."
            )
            abort(404, abort_msg)
        return entry

    def entry_saver(method):
        """
        A decorator to facilitate saving an entry safely.

        This decorator wraps a function that saves an entry. The entry
        must always be a normal entry (not a view) for the save
        operation to succeed, and the saved entry should also be
        validated to ensure that it belongs to an authorized user. This
        method performs both functions: it takes the saved entry and
        queries the database for the up-to-date version, using the
        handler logic to choose either the entry or the corresponding
        view; that process implicitly guarantees authorization.
        """

        @functools.wraps(method)
        def wrapper(cls, *args, **kwargs):
            entry = method(cls, *args, **kwargs)
            # Return either the entry or its view (implicitly confirming authorizatio)
            entry_id = getattr(entry, entry.primary_key_field.name)
            entry = cls.get_entry(entry_id)
            return entry

        return wrapper

    @classmethod
    @entry_saver
    def add_entry(cls, **field_values):
        """
        Create a new entry in the database given field values.

        Parameters
        ----------
        **field_values :
            Values for each field in the entry.

        Returns
        -------
        entry : database.models.Model
            The saved entry.
        """
        entry = cls.model(**field_values)
        cls._db.session.add(entry)
        cls._db.session.flush()
        return entry

    @classmethod
    @entry_saver
    def update_entry(cls, entry_id, **field_values):
        """
        Update an entry in the database given field values.

        Accept a mapping relating given inputs to database fields. This
        mapping is used to update an existing entry in the database. All
        fields are sanitized prior to updating.

        Parameters
        ----------
        entry_id : int
            The ID of the entry to be updated.
        **field_values :
            Values for fields to update in the entry.

        Returns
        -------
        entry : database.models.Model
            The saved entry.
        """
        cls._validate_authorization(entry_id)
        entry = cls._db.session.get(cls.model, entry_id)
        entry_fields = [column.name for column in cls.model.fields]
        for field, value in field_values.items():
            if field not in entry_fields:
                raise ValueError(
                    f"A value cannot be updated in the nonexistent field {field}."
                )
            setattr(entry, field, value)
        cls._db.session.flush()
        return entry

    @classmethod
    def delete_entry(cls, entry_id):
        """
        Delete an entry in the database given its ID.

        Parameters
        ----------
        entry_id : int
            The ID of the entry to be deleted.
        """
        cls._validate_authorization(entry_id)
        entry = cls._db.session.get(cls.model, entry_id)
        cls._db.session.delete(entry)
        cls._db.session.flush()

    @classmethod
    def _validate_authorization(cls, entry_id):
        # Confirm (via access) that the user may manipulate the entry
        return cls.get_entry(entry_id)


class DatabaseViewHandlerMixin(DatabaseHandlerMixin):
    """
    A mixin providing the functionality of a database view handler.

    Note
    ----
    Tools relying on the database view handler functionality may have
    different metaclasses. This mixin allows the functionality of a
    database view handler to be shared by any objects that implement the
    database view handler interface.
    """

    _view_context = False

    def view_query(func):
        """Require that a function use a model view rather than the model."""

        @functools.wraps(func)
        def wrapper(cls, *args, **kwargs):
            orig_view_context = cls._view_context
            cls._view_context = True
            try:
                return_value = func(cls, *args, **kwargs)
            finally:
                cls._view_context = orig_view_context
            return return_value

        return wrapper

    @classmethod
    @view_query
    def get_entries(cls, entry_ids=None, criteria=None, column_orders=None):
        return super().get_entries(
            entry_ids=entry_ids, criteria=criteria, column_orders=column_orders
        )

    @classmethod
    @view_query
    def find_entry(cls, criteria=None, column_orders=None, require_unique=True):
        return super().find_entry(
            criteria=criteria,
            column_orders=column_orders,
            require_unique=require_unique,
        )

    @classmethod
    @view_query
    def get_entry(cls, entry_id):
        return super().get_entry(entry_id)


class DatabaseHandler(DatabaseHandlerMixin, metaclass=DatabaseHandlerMeta):
    """
    A generic handler for database access.

    Database handlers simplify commonly used database interactions.
    Complicated queries can be reformulated as class methods, taking
    variable arguments. The handler also performs user authentication
    upon creation so that user authentication is not required for each
    query.

    Attributes
    ----------
    user_id : int
        The ID of the user who is the subject of database access.
    model : type
        The type of database model that the handler is primarily
        designed to manage.
    table : str
        The name of the database table that this handler manages.
    """

    # All functionality is provided by the mixin


class DatabaseViewHandler(DatabaseViewHandlerMixin, metaclass=DatabaseViewHandlerMeta):
    """
    A generic handler for database view access.

    The view handler imitates the behavior of the standard database
    handler, but with minor customizations to allow the handler to
    operate on database views, rather than native tables.

    Attributes
    ----------
    user_id : int
        The ID of the user who is the subject of database access.
    model : type
        The type of database model that the handler is primarily
        designed to manage.
    table : str
        The name of the database table that this handler manages.
    """

    # All functionality is provided by the mixin
