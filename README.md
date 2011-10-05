Overview
========

Django-Forkit is composed of a set of utility functions for _forking_,
_resetting_, and _diffing_ model objects. Below are a list of the current
utility functions:

forkit.tools.fork
-----------------
Creates and returns a new object that is identical to ``obj``.
- ``fields`` - A list of fields to fork. If a falsy value, the fields
will be inferred depending on the value of ``deep``.
- ``exclude`` - A list of fields to not fork (not applicable if ``fields``
is defined)
- ``deep`` - If ``True``, traversing all related objects and creates forks
of them as well, effectively creating a new _tree_ of objects.
- ``commit`` - If ``True``, all forks (including related objects) will be saved
in the order of dependency. If ``False``, all commits are stashed away until
the root fork is committed.

```python
fork(obj, [fields=None], [exclude=('pk',)], [deep=False], [commit=True])
```

forkit.tools.reset
------------------
Same parameters as above, except that an explicit ``target`` is specified and
will result in an in-place update of ``target``. _Note: currently, deep resets
do not apply to related objects, that is, related objects will be forked rather
than updated in place. This functionality is scheduled for a future release._

```python
reset(obj, target, [fields=None], [exclude=('pk',)], [deep=False], [commit=True])
```

forkit.tools.commit
-------------------
Commits any unsaved changes to a forked or reset object.

```python
commit(obj)
```

forkit.tools.diff
-----------------
Performs a _diff_ between two model objects of the same type. The output is a
``dict`` of differing values relative to ``obj1``. Thus, if ``obj1.foo`` is
``bar`` and ``obj2.foo`` is ``baz``, the output should be ``{'foo': 'baz'}``.
_Note: deep diffs only work for simple non-circular relationships. Improved
functionality is scheduled for a future release._

```python
diff(obj1, obj2, [fields=None], [exclude=('pk',)], [deep=False])
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
