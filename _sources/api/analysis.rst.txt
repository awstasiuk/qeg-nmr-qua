Analysis Module
===============

The analysis module handles data saving/loading, and should eventually include data analysis
routines for common NMR experiments. Specific calibrations routines will re-use identical 
fitting procedures, so these will be implemented here for modularity. A well maintained collection
of analysis tools will facilitate rapid experiment development and deployment, and hopefully 
lead to autonomous machine calibration.


Data Saver
----------

.. automodule:: qeg_nmr_qua.analysis.data_saver
   :members:
   :undoc-members:
   :show-inheritance:
   :exclude-members: _NumpyEncoder
