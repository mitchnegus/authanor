# Authanor

<img src="https://upload.wikimedia.org/wikipedia/commons/1/10/Athanor.jpg" alt="Athanor" />

A tool providing a a Pythonic interface to SQLAlchemy while enforcing authorization criteria for Flask.

SQLAlchemy provides a phenomenal interface for querying a database.
However, this package is designed to enable the construction of handler objects that perform a series of consistent actions on many similar ORM entities.
For example, it is common to want to select all values in a given table using an ORM, or add an entry to the table based on a mapping.
These are easy to do using SQLAlchemy, but my experience is that things get a bit more challenging when a query must be limited to a single authorized user (and several joins are required to filter that query).

It's possible I'm missing a key functionality of SQLAlchemy that enables this behavior elegantly, but I haven't found a clean way to do it yet.
Until I become so enlightened, this package creates an interface where each model may define the chain of joins required to establish whether it belongs to an authorized user, and then a handler to query the database and perform those joins for each query.
This is designed to be extensible, since I often want this behavior available for the majority of ORM models in my application.

If you read this and think "This dude's dumb; why on Earth didn't he use _this_ functionality baked into SQLAlchemy?" drop me a line because I'm interested to know what I'm missing.


## Installation

The _Authanor_ package is registered on the [Python Package Index (PyPI)](https://pypi.org/project/...) for easy installation.
To install the package, simply run

```
$ pip install authanor
```

The package requires a recent version of Python (3.9+).


## License

This project is licensed under the GNU General Public License, Version 3.
It is fully open-source, and while you are more than welcome to fork, add, modify, etc. it is required that you keep any distributed changes and additions open-source.


## Changes

Changes between versions are tracked in the [changelog](CHANGELOG.md).
