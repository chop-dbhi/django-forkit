Overview
========

Abstract model class which adds support for creating deep or shallow
copies (forks) of model instances. Also, adds the ability to _diff_ two
model instances' data.

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

Check out https://github.com/cbmi/django-forkit/blob/master/forkit/tests/models.py
for a more comlicated data model.
