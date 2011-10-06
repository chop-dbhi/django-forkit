from django.db import transaction
from forkit import utils, signals

def _commit_direct(reference, direct=True, deep=False):
    """Recursively set all direct related object references to the
    reference object. Each downstream related object is saved before
    being set.

    ``direct`` should be false if it was already called
    """
    if hasattr(reference, '_forkstate'):
        # get and clear to prevent infinite recursion
        deferred = reference._forkstate.deferred_direct.iteritems()
        reference._forkstate.deferred_direct = {}

        for accessor, value in deferred:
            setval = True
            # execute the commit cycle, but do not actually set anything
            if deep and isinstance(value, utils.DeferProxy):
                value = value.value
                setval = False

            _commit_direct(value, direct=direct, deep=deep)

            if setval:
                # save the object to get a primary key
                setattr(reference, accessor, value)

        # all save triggered by a direct commit must be saved to ensure
        # potential circular references, in addition to not already having
        # a primary key
        if direct or not reference.pk:
            reference.save()

def _commit_related(reference, deep=False):
    if hasattr(reference, '_forkstate'):
        # get and clear to prevent infinite recursion
        deferred = reference._forkstate.deferred_related.iteritems()
        reference._forkstate.deferred_related = {}

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
                setattr(reference, accessor, value)

            # commit all related defers
            if type(value) is list:
                map(lambda x: _commit_related(x, deep=deep), value)
            else:
                _commit_related(value, deep=deep)

@transaction.commit_on_success
def commit_model_object(instance):
    "Recursively commits direct and related objects."
    if not hasattr(instance, '_forkstate'):
        instance.save()
        return

    reference = instance._forkstate.reference
    # pre-signal
    signals.pre_commit.send(sender=reference.__class__, reference=reference, instance=instance)
    # save dependents of this object
    _commit_direct(instance, direct=True, deep=instance._forkstate.deep)
    # depends on ``reference`` having a primary key
    _commit_related(instance, deep=instance._forkstate.deep)
    # post-signal
    signals.post_commit.send(sender=reference.__class__, reference=reference, instance=instance)
