from django.db import models, transaction
from forkit import utils, signals

def _commit_direct(instance, memo):
    """Recursively set all direct related object references to the
    instance object. Each downstream related object is saved before
    being set.
    """
    # get and clear to prevent infinite recursion
    relations = instance._forkstate.deferred_direct.items()
    instance._forkstate.deferred_direct = {}

    for accessor, value in relations:
        _memoize_commit(value, memo=memo)
        # save the object to get a primary key
        setattr(instance, accessor, value)

def _commit_related(instance, memo, stack):
    relations = instance._forkstate.deferred_related.items()
    instance._forkstate.deferred_related = {}

    for accessor, value in relations:
        # execute the commit direct cycle for these related objects,
        if isinstance(value, utils.DeferProxy):
            value = value.value
            if type(value) is list:
                stack.extend(value)
            else:
                stack.append(value)
        else:
            if type(value) is list:
                map(lambda rel: _memoize_commit(rel, memo=memo), value)
            elif isinstance(value, models.Model):
                _memoize_commit(value, memo=memo)

            setattr(instance, accessor, value)

def _memoize_commit(instance, **kwargs):
    if not hasattr(instance, '_forkstate'):
        return instance

    reference = instance._forkstate.reference

    root = False
    memo = kwargs.get('memo', None)
    stack = kwargs.get('stack', [])

    # for every call, keep track of the reference and the object (fork).
    # this is used for recursive calls to related objects. this ensures
    # relationships that follow back up the tree are caught and are merely
    # referenced rather than traversed again.
    if memo is None:
        root = True
        memo = utils.Memo()
    elif memo.has(reference):
        return memo.get(reference)

    memo.add(reference, instance)

    # pre-signal
    signals.pre_commit.send(sender=reference.__class__, reference=reference,
        instance=instance)

    _commit_direct(instance, memo=memo)
    instance.save()
    _commit_related(instance, memo=memo, stack=stack)

    if root:
        for value in iter(stack):
            _memoize_commit(value, memo=memo, stack=[])

    # post-signal
    signals.post_commit.send(sender=reference.__class__, reference=reference,
        instance=instance)

    return instance

@transaction.commit_on_success
def commit_model_object(instance):
    "Recursively commits direct and related objects."
    return _memoize_commit(instance)
