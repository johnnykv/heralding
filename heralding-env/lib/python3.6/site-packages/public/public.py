# Copyright (C) 2016-2017 Barry Warsaw
#
# This project is licensed under the terms of the Apache 2.0 License.  See
# LICENSE.txt for details.

"""Pure-Python implementation."""

import sys


# http://bugs.python.org/issue26632
def public(thing=None, **kws):
    mdict = (sys._getframe(1).f_globals
             if thing is None
             else sys.modules[thing.__module__].__dict__)
    dunder_all = mdict.setdefault('__all__', [])
    if not isinstance(dunder_all, list):
        raise ValueError(
            '__all__ must be a list not: {}'.format(type(dunder_all)))
    if thing is not None:
        dunder_all.append(thing.__name__)
    for key, value in kws.items():
        dunder_all.append(key)
        mdict[key] = value
    return thing
