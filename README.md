# qeg-nmr-qua

NMR Control using the OPX-1000 LF-FEM for solid state nuclear magnetic resonance,
particularly for fluorine (19F) spins.

## Installation

```bash
pip install -e .
```

## Features

- **OPX-1000 Configuration**: Structured configuration management for the OPX-1000 low-frequency front-end module

- **NMR Experiment Builder**: High-level python interface for running complex solid-state NMR Experiments

- **Robust Data Handling**: Experimental data and metadata always saved to file and easily retrievable and reproducible

See the docs here: https://awstasiuk.github.io/qeg-nmr-qua/index.html


## Building the Docs Locally

Install the documentation dependencies (Sphinx and the theme):

```bash
pip install sphinx furo
```

Then build from the `docs/` directory:

```bash
cd docs
python -m sphinx . _build/html
```

Open the result in your browser:

```bash
# Windows
Start-Process _build\html\index.html

# macOS / Linux
open _build/html/index.html
```

The built HTML is written to `docs/_build/html/`. Re-run the `sphinx` command after
any changes to `.rst` files or source docstrings to refresh the output.

## Requirements

- 3.13 > Python >= 3.9
- qm-qua >= 1.1.0
- numpy >= 1.20.0
- matplotlib >= 3.5.0

## License

MIT License - see [LICENSE](LICENSE) for details.
