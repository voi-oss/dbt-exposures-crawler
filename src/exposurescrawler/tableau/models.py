from collections import namedtuple

from typing import Any, MutableMapping, MutableSequence

"""
A lightweight object representing a Tableau workbook. Useful to be used as keys on mappings
before more metadata about the workbooks are extracted from Tableau.
"""
WorkbookReference = namedtuple('WorkbookReference', 'id name')

WorkbookModelsMapping = MutableMapping[WorkbookReference, MutableSequence[Any]]
