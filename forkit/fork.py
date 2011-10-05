from copy import deepcopy
from django.db import models, transaction
from forkit import utils

def _fork_one2one(obj, target, value, field, direct, accessor, deep, cache):
    # if the fork has an existing value, but the reference does not,
    # it cannot be set to None since the field is not nullable. nothing
    # can be done here.
    if not value or not deep:
        if not field.null:
            return

    # for a deep fork, ensure the fork exists, but only add if this is
    # a direct access. since the fork will refer back to ``target``, it's
    # unnecessary to setup the defer twice
    if deep:
        fork = cache.get(value)
        # create a new fork (which will update ``cache``)
        if fork is None:
            fork = fork_model_object(value, deep=deep, cache=cache)

        if not direct:
            fork = utils.DeferProxy(fork)

        target._forkstate.defer_commit(accessor, fork, direct=direct)

def _fork_foreignkey(obj, target, value, field, direct, accessor, deep, cache):
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

        target._forkstate.defer_commit(accessor, fork, direct=direct)
    # nullable direct foreign keys can be set to None
    elif direct and field.null:
        setattr(target, accessor, None)

# TODO add support for ``through`` model
def _fork_many2many(obj, target, value, field, direct, accessor, deep, cache):
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

    target._forkstate.defer_commit(accessor, fork)

def _fork_field(obj, target, accessor, deep, cache):
    """Creates a copy of the reference value for the defined ``accessor``
    (field). For deep forks, each related object is related objects must
    be created first prior to being recursed.
    """
    value, field, direct, m2m = utils._get_field_value(obj, accessor)

    if isinstance(field, models.OneToOneField):
        return _fork_one2one(obj, target, value, field, direct,
            accessor, deep, cache)

    if isinstance(field, models.ForeignKey):
        return _fork_foreignkey(obj, target, value, field, direct,
            accessor, deep, cache)

    if isinstance(field, models.ManyToManyField):
        return _fork_many2many(obj, target, value, field, direct,
            accessor, deep, cache)

    # non-relational field, perform a deepcopy to ensure no mutable nonsense
    setattr(target, accessor, deepcopy(value))

def _reset(obj, target, fields=None, exclude=('pk',), deep=False, commit=True, cache=None):
    "Resets the specified target relative to ``obj``"
    if not isinstance(target, obj.__class__):
        raise TypeError('the object supplied must be of the same type as the reference')

    if not hasattr(target, '_forkstate'):
        # no fields are defined, so get the default ones for shallow or deep
        if not fields:
            fields = utils._default_model_fields(obj, exclude=exclude, deep=deep)

        # for the duration of the reset, each object's state is tracked via
        # the a ForkState object. this is primarily necessary to track
        # deferred commits of related objects
        target._forkstate = utils.ForkState(parent=obj, fields=fields, exclude=exclude)

    elif target._forkstate.has_deferreds:
        target._forkstate.clear_commits()

    target._forkstate.deep = deep

    # for every call, keep track of the reference and the object (fork).
    # this is used for recursive calls to related objects. this ensures
    # relationships that follow back up the tree are caught and are merely
    # referenced rather than traversed again.
    if not cache:
        cache = utils.ForkCache()
    # override commit for non-top level calls
    else:
        commit = False

    cache.add(obj, target)

    # iterate over each field and fork it!. nested calls will not commit,
    # until the recursion has finished
    for accessor in fields:
        _fork_field(obj, target, accessor, deep=deep, cache=cache)

    if commit:
        commit_model_object(target)

    return target

def _commit_direct(obj, direct=True, deep=False):
    """Recursively set all direct related object references to the
    reference object. Each downstream related object is saved before
    being set.

    ``direct`` should be false if it was already called
    """
    if hasattr(obj, '_forkstate'):
        # get and clear to prevent infinite recursion
        deferred = obj._forkstate.deferred_direct.iteritems()
        obj._forkstate.deferred_direct = {}

        for accessor, value in deferred:
            setval = True
            # execute the commit cycle, but do not actually set anything
            if deep and isinstance(value, utils.DeferProxy):
                value = value.value
                setval = False

            _commit_direct(value, direct=direct, deep=deep)

            if setval:
                # save the object to get a primary key
                setattr(obj, accessor, value)

        # all save triggered by a direct commit must be saved to ensure
        # potential circular references, in addition to not already having
        # a primary key
        if direct or not obj.pk:
            obj.save()

def _commit_related(obj, deep=False):
    if hasattr(obj, '_forkstate'):
        # get and clear to prevent infinite recursion
        deferred = obj._forkstate.deferred_related.iteritems()
        obj._forkstate.deferred_related = {}

        for accessor, value in deferred:
            setval = True
            # execute the commit direct cycle for these related objects,
            if isinstance(value, utils.DeferProxy):
                value = value.value
                setval = False

            if type(value) is list:
                map(lambda x: _commit_direct(x, direct=False, deep=deep), value)
            else:
                _commit_direct(value, direct=False, deep=deep)

            if setval:
                setattr(obj, accessor, value)

            # commit all related defers
            if type(value) is list:
                map(lambda x: _commit_related(x, deep=deep), value)
            else:
                _commit_related(value, deep=deep)

def fork_model_object(obj, *args, **kwargs):
    """Creates a fork of the reference object. If an object is supplied, it
    effectively gets reset relative to the reference object.
    """
    target = obj.__class__()
    return _reset(obj, target, *args, **kwargs)

def reset_model_object(obj, target, *args, **kwargs):
    return _reset(obj, target, *args, **kwargs)

@transaction.commit_on_success
def commit_model_object(obj):
    "Recursively commits direct and related objects."
    # save dependents of this object
    _commit_direct(obj, direct=True, deep=obj._forkstate.deep)
    # depends on ``reference`` having a primary key
    _commit_related(obj, deep=obj._forkstate.deep)

