# Copyright (C) 2016-2017 Barry Warsaw
#
# This project is licensed under the terms of the Apache 2.0 License.  See
# LICENSE.txt for details.

import os
import sys
import builtins
import unittest

try:
    from _public import public as c_public
except ImportError:
    # This library was built without the extension module.
    c_public = None
from contextlib import ExitStack, contextmanager
from importlib import import_module
from public import install
from public.public import public as py_public
from tempfile import TemporaryDirectory


@contextmanager
def syspath(directory):
    try:
        sys.path.insert(0, directory)
        yield
    finally:
        assert sys.path[0] == directory
        del sys.path[0]


@contextmanager
def sysmodules():
    modules = sys.modules.copy()
    try:
        yield
    finally:
        sys.modules = modules


class TestPublic(unittest.TestCase):
    import_line = 'from public import public'

    def setUp(self):
        self.resources = ExitStack()
        self.addCleanup(self.resources.close)
        self.tmpdir = self.resources.enter_context(TemporaryDirectory())
        self.resources.enter_context(syspath(self.tmpdir))
        self.resources.enter_context(sysmodules())
        self.modpath = os.path.join(self.tmpdir, 'example.py')

    def test_atpublic_function(self):
        with open(self.modpath, 'w', encoding='utf-8') as fp:
            print("""\
{}

@public
def a_function():
    pass
""".format(self.import_line), file=fp)
        module = import_module('example')
        self.assertEqual(module.__all__, ['a_function'])

    def test_atpublic_function_runnable(self):
        with open(self.modpath, 'w', encoding='utf-8') as fp:
            print("""\
{}

@public
def a_function():
    return 1
""".format(self.import_line), file=fp)
        module = import_module('example')
        self.assertEqual(module.a_function(), 1)

    def test_atpublic_class(self):
        with open(self.modpath, 'w', encoding='utf-8') as fp:
            print("""\
{}

@public
class AClass:
    pass
""".format(self.import_line), file=fp)
        module = import_module('example')
        self.assertEqual(module.__all__, ['AClass'])

    def test_atpublic_class_runnable(self):
        with open(self.modpath, 'w', encoding='utf-8') as fp:
            print("""\
{}

@public
class AClass:
    pass
""".format(self.import_line), file=fp)
        module = import_module('example')
        self.assertIsInstance(module.AClass(), module.AClass)

    def test_atpublic_two_things(self):
        with open(self.modpath, 'w', encoding='utf-8') as fp:
            print("""\
{}

@public
def foo():
    pass

@public
class AClass:
    pass
""".format(self.import_line), file=fp)
        module = import_module('example')
        self.assertEqual(module.__all__, ['foo', 'AClass'])

    def test_atpublic_append_to_all(self):
        with open(self.modpath, 'w', encoding='utf-8') as fp:
            print("""\
__all__ = ['a', 'b']

a = 1
b = 2

{}

@public
def foo():
    pass

@public
class AClass:
    pass
""".format(self.import_line), file=fp)
        module = import_module('example')
        self.assertEqual(module.__all__, ['a', 'b', 'foo', 'AClass'])

    def test_atpublic_keywords(self):
        with open(self.modpath, 'w', encoding='utf-8') as fp:
            print("""\
{}

public(a=1, b=2)
""".format(self.import_line), file=fp)
        module = import_module('example')
        self.assertEqual(sorted(module.__all__), ['a', 'b'])

    def test_atpublic_keywords_multicall(self):
        with open(self.modpath, 'w', encoding='utf-8') as fp:
            print("""\
{}

public(b=1)
public(a=2)
""".format(self.import_line), file=fp)
        module = import_module('example')
        self.assertEqual(module.__all__, ['b', 'a'])

    def test_atpublic_keywords_global_bindings(self):
        with open(self.modpath, 'w', encoding='utf-8') as fp:
            print("""\
{}

public(a=1, b=2)
""".format(self.import_line), file=fp)
        module = import_module('example')
        self.assertEqual(module.a, 1)
        self.assertEqual(module.b, 2)

    def test_atpublic_mixnmatch(self):
        with open(self.modpath, 'w', encoding='utf-8') as fp:
            print("""\
__all__ = ['a', 'b']

a = 1
b = 2

{}

@public
def foo():
    pass

@public
class AClass:
    pass

public(c=3)
""".format(self.import_line), file=fp)
        module = import_module('example')
        self.assertEqual(module.__all__, ['a', 'b', 'foo', 'AClass', 'c'])

    def test_all_is_a_tuple(self):
        with open(self.modpath, 'w', encoding='utf-8') as fp:
            print("""\
__all__ = ('foo',)

{}

def foo():
    pass

@public
def bar():
    pass
""".format(self.import_line), file=fp)
        self.assertRaises(ValueError, import_module, 'example')


class TestPyPublic(TestPublic):
    import_line = 'from public import py_public as public'


class TestInstall(unittest.TestCase):
    @unittest.skipIf(c_public is None, 'Built without the extension module')
    def test_install_c_public(self):
        self.assertFalse(hasattr(builtins, 'public'))
        self.addCleanup(delattr, builtins, 'public')
        install()
        self.assertTrue(hasattr(builtins, 'public'))
        self.assertIs(builtins.public, c_public)

    def test_install_py_public(self):
        self.assertFalse(hasattr(builtins, 'public'))
        self.addCleanup(delattr, builtins, 'public')
        install()
        self.assertTrue(hasattr(builtins, 'public'))
        self.assertIs(builtins.public, c_public or py_public)
