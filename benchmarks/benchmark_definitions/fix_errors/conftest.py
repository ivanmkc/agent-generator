import os
import sys

import pytest


@pytest.fixture(autouse=True)
def add_case_dir_to_path(request):
  """
  Automatically adds the directory of the running test file to sys.path.
  This allows 'import fixed' and 'import unfixed' to work inside any test case.
  Also clears 'fixed' and 'unfixed' from sys.modules to force reload.
  """
  case_dir = os.path.dirname(request.module.__file__)

  # Clean up sys.modules before the test
  for module_name in ["fixed", "unfixed"]:
    if module_name in sys.modules:
      del sys.modules[module_name]

  if case_dir not in sys.path:
    sys.path.insert(0, case_dir)
    yield
    # cleanup after test
    sys.path.pop(0)
  else:
    yield

  # Clean up sys.modules after the test
  for module_name in ["fixed", "unfixed"]:
    if module_name in sys.modules:
      del sys.modules[module_name]
