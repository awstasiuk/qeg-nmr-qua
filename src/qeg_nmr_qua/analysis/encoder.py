import json
from pathlib import Path
from numpy import ndarray, integer, floating, bool_  # type: ignore


class QuantumEncoder(json.JSONEncoder):
    """JSON encoder for scientific computing and quantum experiment data.

    Extends the standard json.JSONEncoder to support NumPy types and Path objects
    commonly used in quantum computing and scientific experiments:

    **Type Conversions:**

    - ``numpy.ndarray`` → list (recursively converts all elements)
    - ``numpy.integer`` (int8, int32, int64, etc.) → int
    - ``numpy.floating`` (float32, float64) → float
    - ``numpy.bool_`` → bool
    - ``pathlib.Path`` → str

    This enables seamless serialization of arrays and scientific data structures
    that are common in NMR experiments without manual conversion.

    The class is designed to work with :class:`DataSaver` for persisting experiment
    data to JSON files while preserving numerical precision and file paths.

    Example:
        >>> import json
        >>> import numpy as np
        >>> data = {"arr": np.array([1, 2, 3]), "val": np.float32(3.14)}
        >>> json.dumps(data, cls=QuantumEncoder)
        '{"arr": [1, 2, 3], "val": 3.140000104904175}'
    """

    def default(self, obj):
        """Encode numpy types and Path objects as JSON-serializable Python types."""
        if isinstance(obj, ndarray):
            return obj.tolist()
        elif isinstance(obj, (integer, floating)):
            return obj.item()
        elif isinstance(obj, bool_):
            return bool(obj)
        elif isinstance(obj, Path):
            return str(obj)
        return super().default(obj)
