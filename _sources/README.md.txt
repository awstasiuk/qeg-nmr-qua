# Documentation

This directory contains the Sphinx documentation for `qeg-nmr-qua`.

## Building the Documentation

### Prerequisites

Install documentation dependencies:

```bash
pip install -e ".[docs]"
```

### Build HTML Documentation

On Windows:

```bash
cd docs
.\make.bat html
```

On Linux/macOS:

```bash
cd docs
make html
```

The generated HTML documentation will be in `docs/_build/html/`.

### View the Documentation

Open `docs/_build/html/index.html` in your web browser. It is recommended
to have the "open in browser" VScode extension to make this simple. Or, run:

From the project root:
```bash
cd docs
python -m http.server --directory docs/_build/html
```

Or from the `docs` directory:
```bash
python -m http.server --directory _build/html
```

Then navigate to http://localhost:8000 in your browser. This appears to be much
less stable than simply using the "open in browser" extension.

## Documentation Structure

- `index.rst` - Main documentation homepage
- `installation.rst` - Installation instructions
- `quickstart.rst` - Quick start guide
- `api/` - Automatic API documentation generated from docstrings
  - `index.rst` - API reference index
  - `config.rst` - Configuration module documentation
  - `experiment.rst` - Experiment module documentation
  - `analysis.rst` - Analysis module documentation
  - `spectroscopy.rst` - Spectroscopy module documentation
- `conf.py` - Sphinx configuration file

## Making Changes

1. Edit the `.rst` files in the `docs/` directory
2. Rebuild the documentation with `make html` or `make.bat html`
3. Refresh your browser to see the changes

The API documentation is automatically generated from docstrings in the source code, so update the docstrings in the Python files to change the API documentation.
