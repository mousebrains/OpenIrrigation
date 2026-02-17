import sys
import types

# Provide stub psycopg2 so scheduler modules can be imported without the real driver
def _install_psycopg2_stub():
    if 'psycopg2' not in sys.modules:
        pg2 = types.ModuleType('psycopg2')
        pg2.extensions = types.ModuleType('psycopg2.extensions')
        pg2.extras = types.ModuleType('psycopg2.extras')
        pg2.extensions.cursor = type('cursor', (), {})
        pg2.extensions.connection = type('connection', (), {})
        pg2.Warning = Warning
        pg2.Error = Exception
        sys.modules['psycopg2'] = pg2
        sys.modules['psycopg2.extensions'] = pg2.extensions
        sys.modules['psycopg2.extras'] = pg2.extras

_install_psycopg2_stub()

# Provide stub astral so SchedProgram can be imported without the real package
if 'astral' not in sys.modules:
    astral_mod = types.ModuleType('astral')
    astral_mod.Location = type('Location', (), {})
    sys.modules['astral'] = astral_mod

# Provide stub for other missing modules
for _mod_name in ('serial', 'Notify', 'Params', 'MyLogger'):
    if _mod_name not in sys.modules:
        sys.modules[_mod_name] = types.ModuleType(_mod_name)

# Pre-import SchedMain to resolve the circular import:
#   SchedAction -> SchedMain -> SchedTimeline -> SchedAction
# In production this works because scheduler.py imports SchedMain first.
import SchedMain  # noqa: E402

import pytest
import logging
from helpers import MockSensor, MockProgramStation


@pytest.fixture
def logger():
    return logging.getLogger('test')


@pytest.fixture
def mock_sensor():
    def _factory(**kwargs):
        return MockSensor(**kwargs)
    return _factory


@pytest.fixture
def mock_program_station():
    def _factory(**kwargs):
        if 'logger' not in kwargs:
            kwargs['logger'] = logging.getLogger('test')
        return MockProgramStation(**kwargs)
    return _factory
