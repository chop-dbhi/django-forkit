from copy import deepcopy
from django.db import models
from forkit import utils, signals
from forkit.commit import commit_model_object

def _fork_one2one(reference, instance, value, field, direct, accessor, deep, cache):
    # if the fork has an existing value, but the reference does not,
    # it cannot be set to None since the field is not nullable. nothing
    # can be done here.
    if not value or not deep:
        if not field.null:
            return

    # for a deep fork, ensure the fork exists, but only add if this is
    # a direct access. since the fork will refer back to ``instance``, it's
    # unnecessary to setup the defer twice
    if deep:
        fork = cache.get(value)
        # create a new fork (which will update ``cache``)
        if fork is None:
            fork = fork_model_object(value, deep=deep, cache=cache)

        if not direct:
            fork = utils.DeferProxy(fork)

        instance._forkstate.defer_commit(accessor, fork, direct=direct)

def _fork_foreignkey(reference, instance, value, field, direct, accessor, deep, cache):
    # direct foreign keys used as is (shallow) or forked (deep). for deep
    # forks, the association to the new objects will be defined on the
    # directly accessed object

    if value:
        if direct and deep:
            fork = cache.get(value)
            # create a new fork (which will update ``cache``)
            if fork is None:
                fork = fork_model_object(value, deep=deep, cache=cache)

        # iterate over each object in the related set
        elif not direct and deep:
            fork = []
            for rel in value:
                f = cache.get(rel)
                if f is None:
                    f = fork_model_object(rel, deep=deep, cache=cache)
                fork.append(f)

            fork = utils.DeferProxy(fork)
        else:
            fork = value

        instance._forkstate.defer_commit(accessor, fork, direct=direct)
    # nullable direct foreign keys can be set to None
    elif direct and field.null:
        setattr(instance, accessor, None)

def _fork_many2many(reference, instance, value, field, direct, accessor, deep, cache):
    if not value:
        return

    if not deep:
        fork = value
    else:
        fork = []
        for rel in value:
            f = cache.get(rel)
            if f is None:
                f = fork_model_object(rel, deep=deep, cache=cache)
            fork.append(f)

        if not direct:
            fork = utils.DeferProxy(fork)

    instance._forkstate.defer_commit(accessor, fork)

def _fork_field(reference, instance, accessor, deep, cache):
    """Creates a copy of the reference value for the defined ``accessor``
    (field). For deep forks, each related object is related objects must
    be created first prior to being recursed.
    """
    value, field, direct, m2m = utils._get_field_value(reference, accessor)

    if isinstance(field, models.OneToOneField):
        return _fork_one2one(reference, instance, value, field, direct,
            accessor, deep, cache)

    if isinstance(field, models.ForeignKey):
        return _fork_foreignkey(reference, instance, value, field, direct,
            accessor, deep, cache)

    if isinstance(field, models.ManyToManyField):
        return _fork_many2many(reference, instance, value, field, direct,
            accessor, deep, cache)

    # non-relational field, perform a deepcopy to ensure no mutable nonsense
    setattr(instance, accessor, deepcopy(value))

def _fork(reference, instance, fields=None, exclude=('pk',), deep=False, commit=True, cache=None):
    "Resets the specified instance relative to ``reference``"
    if not isinstance(instance, reference.__class__):
        raise TypeError('the object supplied must be of the same type as the reference')

    # no fields are defined, so get the default ones for shallow or deep
    if not fields:
        fields = utils._default_model_fields(reference, exclude=exclude, deep=deep)

    if not hasattr(instance, '_forkstate'):
        # for the duration of the fork, each object's state is tracked via
        # the a ForkState object. this is primarily necessary to track
        # deferred commits of related objects
        instance._forkstate = utils.ForkState(reference=reference)

    elif instance._forkstate.has_deferreds:
        instance._forkstate.clear_commits()

    instance._forkstate.deep = deep

    # for every call, keep track of the reference and the object (fork).
    # this is used for recursive calls to related objects. this ensures
    # relationships that follow back up the tree are caught and are merely
    # referenced rather than traversed again.
    if not cache:
        cache = utils.ForkCache()
    # override commit for non-top level calls
    else:
        commit = False

    cache.add(reference, instance)

    # iterate over each field and fork it!. nested calls will not commit,
    # until the recursion has finished
    for accessor in fields:
        _fork_field(reference, instance, accessor, deep=deep, cache=cache)

    if commit:
        commit_model_object(instance)

    return instance

def fork_model_object(reference, **kwargs):
    """Creates a fork of the reference object. If an object is supplied, it
    effectively gets reset relative to the reference object.
    """
    # initialize new instance
    instance = reference.__class__()
    # pre-signal
    signals.pre_fork.send(sender=reference.__class__, reference=reference,
        instance=instance, config=kwargs)
    _fork(reference, instance, **kwargs)
    # post-signal
    signals.post_fork.send(sender=reference.__class__, reference=reference,
        instance=instance)
    return instance
