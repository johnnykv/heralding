# Copyright (C) 2016-2017 Barry Warsaw
#
# This project is licensed under the terms of the Apache 2.0 License.  See
# LICENSE.txt for details.

"""@public -- populate __all__"""

from public.public import public as py_public
try:
    from _public import public as c_public
except ImportError:                                 # pragma: nocover
    # This library was built without the extension module.
    c_public = None


__version__ = '1.0'


if c_public is None:                                # pragma: nocover
    py_public(public=py_public)
    py_public(py_public=py_public)
else:                                               # pragma: nocover
    c_public(public=c_public)
    c_public(py_public=py_public)


def install():
    """Install @public into builtins."""
    import builtins
    builtins.public = c_public or py_public
