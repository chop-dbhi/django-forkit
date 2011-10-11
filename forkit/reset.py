from copy import deepcopy
from django.db import models
from forkit import utils, signals
from forkit.commit import commit_model_object

def _reset_one2one(instance, refvalue, field, direct, accessor, deep, **kwargs):
    value = utils._get_field_value(instance, accessor)[0]
    if refvalue and value and deep:
        _memoize_reset(refvalue, value, deep=deep, **kwargs)
        instance._commits.defer(accessor, value, direct=direct)

def _reset_foreignkey(instance, refvalue, field, direct, accessor, deep, **kwargs):
    value = utils._get_field_value(instance, accessor)[0]
    if refvalue and value and deep:
        _memoize_reset(refvalue, value, deep=deep, **kwargs)
    # for shallow or when value is None, use the reference value
    elif not value:
        value = refvalue

    instance._commits.defer(accessor, value, direct=direct)

def _reset_field(reference, instance, accessor, **kwargs):
    """Creates a copy of the reference value for the defined ``accessor``
    (field). For deep forks, each related object is related objects must
    be created first prior to being recursed.
    """
    value, field, direct, m2m = utils._get_field_value(reference, accessor)

    # explicitly block reverse and m2m relationships..
    if not direct or m2m:
        return

    kwargs['commit'] = False

    if isinstance(field, models.OneToOneField):
        return _reset_one2one(instance, value, field, direct,
            accessor, **kwargs)

    if isinstance(field, models.ForeignKey):
        return _reset_foreignkey(instance, value, field, direct,
            accessor, **kwargs)

    # non-relational field, perform a deepcopy to ensure no mutable nonsense
    setattr(instance, accessor, deepcopy(value))

def _memoize_reset(reference, instance, **kwargs):
    "Resets the specified instance relative to ``reference``"
    # popped so it does not get included in the config for the signal
    memo = kwargs.pop('memo', None)

    # for every call, keep track of the reference and the object (fork).
    # this is used for recursive calls to related objects. this ensures
    # relationships that follow back up the tree are caught and are merely
    # referenced rather than traversed again.
    if memo is None:
        memo = utils.Memo()
    elif memo.has(reference):
        return memo.get(reference)

    if not isinstance(instance, reference.__class__):
        raise TypeError('The instance supplied must be of the same type as the reference')

    instance._commits = utils.Commits(reference)
    memo.add(reference, instance)

    # default configuration
    config = {
        'fields': None,
        'exclude': ['pk'],
        'deep': False,
        'commit': True,
    }

    # update with user-defined
    config.update(kwargs)

    # pre-signal
    signals.pre_reset.send(sender=reference.__class__, reference=reference,
        instance=instance, config=config, **kwargs)

    fields = config['fields']
    exclude = config['exclude']
    deep = config['deep']
    commit = config['commit']

    # no fields are defined, so get the default ones for shallow or deep
    if not fields:
        fields = utils._default_model_fields(reference, exclude=exclude, deep=deep)

    kwargs.update({'deep': deep})

    # iterate over each field and fork it!. nested calls will not commit,
    # until the recursion has finished
    for accessor in fields:
        _reset_field(reference, instance, accessor, **kwargs)

    # post-signal
    signals.post_reset.send(sender=reference.__class__, reference=reference,
        instance=instance, **kwargs)

    if commit:
        commit_model_object(instance)

    return instance

def reset_model_object(reference, instance, **kwargs):
    "Resets the ``instance`` object relative to ``reference``'s state."
    return _memoize_reset(reference, instance, **kwargs)
