# Changelog


## 1.0.0

- Initial release

### 1.0.1

- Fix display for the "fancy README" on PyPI

### 1.0.2

- Include a `db_transaction` decorator for wrapping Flask app routes that represent database transactions
- Add more `AppTestManager` object arguments (and stop requiring inheritance override)

### 1.1.0

- Factored out the majority of app/db testing code and moved it to the Fuisce package (now included as a dependency)

### 1.1.1

- Pass keyword arguments through `DatabaseViewHandlerMixin` mixin `get_entries` method to parent
- Fixed source code formatting
