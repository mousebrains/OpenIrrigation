"""Tests for Params: __toNum and __decode internal helpers."""

import sys

# Remove the conftest stub so we can import the real module.
# Also need real DB stub since Params does `from DB import DB`.
sys.modules.pop('Params', None)
if 'DB' not in sys.modules:
    import types
    _db_mod = types.ModuleType('DB')
    _db_mod.DB = type('DB', (), {})
    sys.modules['DB'] = _db_mod

import Params  # noqa: E402

# Module-level private functions use single underscore prefix
_toNum = Params.__dict__['_Params__toNum'] if '_Params__toNum' in Params.__dict__ else None

# For module-level (non-class) names Python doesn't mangle, so look for raw name
if _toNum is None:
    for _name, _obj in Params.__dict__.items():
        if 'toNum' in _name and callable(_obj):
            _toNum = _obj
            break

_decode = None
for _name, _obj in Params.__dict__.items():
    if 'decode' in _name and callable(_obj):
        _decode = _obj
        break


class TestToNum:
    def test_integer(self):
        assert _toNum('42') == 42
        assert isinstance(_toNum('42'), int)

    def test_float(self):
        assert _toNum('3.14') == 3.14
        assert isinstance(_toNum('3.14'), float)

    def test_string(self):
        assert _toNum('hello') == 'hello'

    def test_string_with_spaces(self):
        assert _toNum('  hello  ') == 'hello'


class TestDecode:
    def test_none(self):
        assert _decode(None) is None

    def test_simple_int(self):
        assert _decode('42') == 42

    def test_simple_float(self):
        assert _decode('3.14') == 3.14

    def test_simple_string(self):
        assert _decode('hello') == 'hello'

    def test_csv_all_numeric(self):
        result = _decode('1,2,3')
        assert result == [1, 2, 3]

    def test_csv_mixed_keeps_string(self):
        result = _decode('1,two,3')
        assert result == '1,two,3'

    def test_csv_floats(self):
        result = _decode('1.1,2.2')
        assert result == [1.1, 2.2]

    def test_whitespace_stripped(self):
        assert _decode('  hello  ') == 'hello'
