import sys
import types

# Provide stub psycopg so scheduler modules can be imported without the real driver
def _install_psycopg_stub():
    if 'psycopg' not in sys.modules:
        pg = types.ModuleType('psycopg')
        pg.sql = types.ModuleType('psycopg.sql')
        pg.rows = types.ModuleType('psycopg.rows')
        pg.sql.SQL = lambda fmt: type('SQL', (), {'format': lambda self, *a, **kw: ''})()
        pg.sql.Identifier = lambda name: name
        pg.sql.Literal = lambda val: type('Literal', (), {'as_string': lambda self, ctx: repr(val)})()
        pg.rows.dict_row = None  # sentinel for row_factory
        pg.Cursor = type('Cursor', (), {})
        pg.Connection = type('Connection', (), {})
        pg.Warning = Warning
        pg.Error = Exception
        sys.modules['psycopg'] = pg
        sys.modules['psycopg.sql'] = pg.sql
        sys.modules['psycopg.rows'] = pg.rows

_install_psycopg_stub()

# Provide stub astral so SchedProgram can be imported without the real package
if 'astral' not in sys.modules:
    astral_mod = types.ModuleType('astral')
    astral_mod.Location = type('Location', (), {})
    sys.modules['astral'] = astral_mod

# Provide stub for other missing modules
for _mod_name in ('serial', 'Notify', 'Params'):
    if _mod_name not in sys.modules:
        _stub = types.ModuleType(_mod_name)
        if _mod_name == 'serial':
            _stub.Serial = type('Serial', (), {})
        sys.modules[_mod_name] = _stub

# MyLogger stub needs addArgs and mkLogger to support AgriMet module-level code
if 'MyLogger' not in sys.modules:
    _ml = types.ModuleType('MyLogger')
    _ml.addArgs = lambda parser: None
    _ml.mkLogger = lambda args, name: __import__('logging').getLogger(name)
    sys.modules['MyLogger'] = _ml

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
