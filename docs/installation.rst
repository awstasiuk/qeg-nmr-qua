Installation
============

Requirements
------------

* Python >= 3.9, < 3.13
* qm-qua >= 1.1.0
* numpy >= 1.20.0
* matplotlib >= 3.5.0
* h5py >= 3.0.0

Install from Source
-------------------

Clone the repository and install in editable mode:

.. code-block:: bash

   git clone https://github.com/awstasiuk/qeg-nmr-qua.git
   cd qeg-nmr-qua
   pip install -e .

Development Installation
------------------------

For development, install with additional dependencies:

.. code-block:: bash

   pip install -e ".[dev]"

This includes:

* pytest >= 7.0.0
* pytest-cov >= 4.0.0
* ruff >= 0.1.0
