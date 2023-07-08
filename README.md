# Authanor

<img src="https://upload.wikimedia.org/wikipedia/commons/1/10/Athanor.jpg" alt="Athanor" />

A tool providing a a Pythonic interface to SQLAlchemy while enforcing authorization criteria for Flask.

SQLAlchemy provides a solid interface for managing database operations.
However, this package is designed to enable the construction of handler objects that perform a series of consistent actions on many similar ORM entities.
For example, I find that I frequently want to select all values (for specific columns) in a given table using an ORM or add an entry to the table based on a mapping.
At the same time, I want to rigorously test my databases—but not pay the penalty for reconstructing the database for _every_ test.


### Authorizations & Database Handlers

The common operations are easy to do using SQLAlchemy, but rather than rolling new functions for each new query in every application, this tool provides a set of handlers that are designed to abstract away a bunch of the tedious details.
Also, my experience is that enforcing authorization constraints when manipulating sophisticated table relationships can be tricky, and so this tool and its handlers provide an interface for managing those authorizations consistently.

It's possible I'm missing a key functionality of SQLAlchemy that enables this behavior elegantly, but I haven't found a satisfiably clean way to do it yet.
Until I become so enlightened, this package creates an interface where each model may define the chain of joins required to establish whether it belongs to an authorized user, and then a handler to query the database and perform those joins for each query.
This is designed to be extensible, since I often want this behavior available for the majority of ORM models in my application.

If you read this and think "This dude's dumb; why on Earth didn't he use _this_ functionality baked into SQLAlchemy?" drop me a line because I'm interested to know what I'm missing.


## Installation

The _Authanor_ package is registered on the [Python Package Index (PyPI)](https://pypi.org/project/authanor) for easy installation.
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
