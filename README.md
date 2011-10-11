Overview
========
Django-Forkit is composed of a set of utility functions for _forking_,
_resetting_, and _diffing_ model objects. Below are a list of the current
utility functions:

forkit.tools.fork
-----------------
Creates and returns a new object that is identical to ``reference``.

- ``fields`` - A list of fields to fork. If a falsy value, the fields
will be inferred depending on the value of ``deep``.
- ``exclude`` - A list of fields to not fork (not applicable if ``fields``
is defined)
- ``deep`` - If ``True``, traversing all related objects and creates forks
of them as well, effectively creating a new _tree_ of objects.
- ``commit`` - If ``True``, all forks (including related objects) will be saved
in the order of dependency. If ``False``, all commits are stashed away until
the root fork is committed.
- ``**kwargs`` - Any additional keyword arguments are passed along to all signal
receivers. Useful for altering runtime behavior in signal receivers.

```python
fork(reference, [fields=None], [exclude=('pk',)], [deep=False], [commit=True], [**kwargs])
```

forkit.tools.reset
------------------
Same parameters as above, except that an explicit ``instance`` is rquired and
will result in an in-place update of ``instance``. For shallow resets, only the
local non-relational fields will be updated. For deep resets, _direct_
foreign keys will be traversed and reset. _Many-to-many and reverse foreign keys
are not attempted to be reset because the comparison between the related objects
for ``reference`` and the related objects for ``instance`` becomes ambiguous._

```python
reset(reference, instance, [fields=None], [exclude=('pk',)], [deep=False], [commit=True], [**kwargs])
```

forkit.tools.commit
-------------------
Commits any unsaved changes to a forked or reset object.

```python
commit(reference, [**kwargs])
```

forkit.tools.diff
-----------------
Performs a _diff_ between two model objects of the same type. The output is a
``dict`` of differing values relative to ``reference``. Thus, if
``reference.foo`` is ``bar`` and ``instance.foo`` is ``baz``, the output will
be ``{'foo': 'baz'}``. _Note: deep diffs only work for simple non-circular
relationships. Improved functionality is scheduled for a future release._

```python
diff(reference, instance, [fields=None], [exclude=('pk',)], [deep=False], [**kwargs])
```

ForkableModel
-------------
Also included is a ``Model`` subclass which has implements the above functions
as methods.

```python
from forkit.models import ForkableModel

class Author(ForkableModel):
    first_name = models.CharField(max_length=30)
    last_name = models.CharField(max_length=30)
```

Let's create starting object:

```python
author = Author(first_name='Byron', last_name='Ruth')
author.save()
```

To create copy, simply call the ``fork`` method.

```python
author_fork = author.fork()
```

When an object is forked, it immediately inherits it's data including
related objects.

```python
author_fork.first_name # Byron
author_fork.last_name # Ruth
```

Let us change something on the fork and use the ``diff`` method to compare it
against the original ``author``. It returns a dictionary of the differences
between itself and the passed in object.

```python
author_fork.first_name = 'Edward'
author_fork.diff(author) # {'first_name': 'Edward'}
```

Once satisfied with the changes, simply call ``commit``.

```python
author_fork.commit()
```

Signals
=======
For each of the utility function above, ``pre_FOO`` and ``post_FOO`` signals
are sent allowing for a decoupled approached for customizing behavior, especially
when performing deep operations.

forkit.signals.pre_fork
-----------------------

- ``sender`` - the model class of the instance
- ``reference`` - the reference object the fork is being created from
- ``instance`` - the forked object itself
- ``config`` - a ``dict`` of the keyword arguments passed into ``forkit.tools.fork``

forkit.signals.post_fork
-----------------------

- ``sender`` - the model class of the instance
- ``reference`` - the reference object the fork is being created from
- ``instance`` - the forked object itself

forkit.signals.pre_reset
-----------------------

- ``sender`` - the model class of the instance
- ``reference`` - the reference object the instance is being reset relative to
- ``instance`` - the object being reset
- ``config`` - a ``dict`` of the keyword arguments passed into ``forkit.tools.reset``

forkit.signals.post_reset
-----------------------

- ``sender`` - the model class of the instance
- ``reference`` - the reference object the instance is being reset relative to
- ``instance`` - the object being reset

forkit.signals.pre_commit
-----------------------

- ``sender`` - the model class of the instance
- ``reference`` - the reference object the instance has been derived
- ``instance`` - the object to be committed

forkit.signals.post_commit
-----------------------

- ``sender`` - the model class of the instance
- ``reference`` - the reference object the instance has been derived
- ``instance`` - the object that has been committed

forkit.signals.pre_diff
-----------------------

- ``sender`` - the model class of the instance
- ``reference`` - the reference object the instance is being diffed against
- ``instance`` - the object being diffed with
- ``config`` - a ``dict`` of the keyword arguments passed into ``forkit.tools.diff``

forkit.signals.post_diff
-----------------------

- ``sender`` - the model class of the instance
- ``reference`` - the reference object the instance is being diffed against
- ``instance`` - the object being diffed with
- ``diff`` - the diff between the ``reference`` and ``instance``
