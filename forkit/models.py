from copy import deepcopy
from django.db import models, transaction
from django.db.models import related

class DeferProxy(object):
    def __init__(self, value):
        self.value = value

    def __repr__(self):
        return '<DeferProxy: "{0}">'.format(repr(self.value))

class ForkState(object):
    """Encapulates all state of a forked model object.

        ``ref`` - reference to the model object it represents
        ``parent`` - reference to the mode object this object was forked from
        ``fields`` - list field names used to fork the object
        ``exclude`` - exclude fields from the default set
    """
    def __init__(self, parent, fields, exclude):
        self.parent = parent
        self.fields = fields
        self.exclude = exclude

        self.deferred_direct = {}
        self.deferred_related = {}

    def clear_commits(self):
        self.deferred_direct = {}
        self.deferred_related = {}

    def defer_commit(self, accessor, obj, direct=False):
        "Add object in the deferred queue for the given accessor."
        if direct:
            self.deferred_direct[accessor] = obj
        else:
            self.deferred_related[accessor] = obj

    @property
    def has_deferreds(self):
        "Test whether there are pending commits."
        return self.deferred_direct or self.deferred_related

    def get_deferred(self, accessor, direct=False):
        "Get a deferred fork by the given accessor."
        if direct:
            return self.deferred_direct.get(accessor, None)
        return self.deferred_related.get(accessor, None)


class ForkCache(object):
    "Cache references to saved or unsaved forks during a deep fork."
    def __init__(self):
        self._cache = {}

    def get(self, obj):
        key = obj.pk and (obj.__class__, obj.pk) or obj
        return self._cache.get(key)

    def add(self, obj, value):
        key = obj.pk and (obj.__class__, obj.pk) or obj
        self._cache[key] = value


class ForkableModel(models.Model):

    def _get_field_by_accessor(self, accessor):
        """Extends the model ``Options.get_field_by_name`` to look up reverse
        relationships by their accessor name. This gets cached on the first
        lookup.

        The cache will only be needed when the ``related_name`` attribute has
        not been set for reverse relationships.
        """
        try:
            field, model, direct, m2m = self._meta.get_field_by_name(accessor)

            if isinstance(field, related.RelatedObject):
                field = field.field
        # if this occurs, try related object accessor
        except models.FieldDoesNotExist, e:
            # check to see if this cache has been set
            if not hasattr(self._meta, 'related_objects_by_accessor'):
                cache = {}

                # reverse foreign key and many-to-many rels
                related_objects = (
                    self._meta.get_all_related_objects() +
                    self._meta.get_all_related_many_to_many_objects()
                )

                for rel in iter(related_objects):
                    cache[rel.get_accessor_name()] = rel

                self._meta.related_objects_by_accessor = cache

            rel = self._meta.related_objects_by_accessor.get(accessor, None)

            # if the related object still doesn't exist, raise the exception
            # that is present
            if rel is None:
                raise e

            field, model, direct, m2m = (
                rel.field,
                rel.model,
                False,
                isinstance(rel.field, models.ManyToManyField)
            )

        # ignoring ``model`` for now.. no use for it
        return field, direct, m2m

    def _get_field_value(self, accessor):
        """Simple helper that returns the model's data value and catches
        non-existent related object lookups.
        """
        field, direct, m2m = self._get_field_by_accessor(accessor)

        value = None
        # attempt to retrieve deferred values first, since they will be
        # the value once comitted. these will never contain non-relational
        # fields
        if hasattr(self, '_forkstate') and self._forkstate.has_deferreds:
            if m2m:
                value = self._forkstate.get_deferred(accessor, direct=False)
            else:
                value = self._forkstate.get_deferred(accessor, direct=direct)
            if value and isinstance(value, DeferProxy):
                value = value.value

        # deferred relations can never be a NoneType
        if value is None:
            try:
                value = getattr(self, accessor)
            # catch foreign keys and one-to-one lookups
            except models.ObjectDoesNotExist:
                value = None
            # catch many-to-many or related foreign keys
            except ValueError:
                value = []

        # get the queryset associated with the m2m or reverse foreign key.
        # logic broken up for readability
        if value and m2m or not direct and not isinstance(field, models.OneToOneField):
            if type(value) is not list:
                value = value.all()

        # ignoring ``model`` for now.. no use for it
        return value, field, direct, m2m

    def _default_model_fields(self, exclude=('pk',), deep=False):
        "Aggregates the default set of fields for creating an object fork."
        if not exclude:
            exclude = []
        # handle this special case..
        else:
            exclude = list(exclude)
            if 'pk' in exclude:
                exclude.remove('pk')
                exclude.append(self._meta.pk.name)

        fields = (
            [f.name for f in self._meta.fields + self._meta.many_to_many] +
            [r.get_accessor_name() for r in self._meta.get_all_related_many_to_many_objects()]
        )

        if deep:
            fields += [r.get_accessor_name() for r in self._meta.get_all_related_objects()]

        return set(fields) - set(exclude)

    # below contains all the necessary logic handling values for each
    # relation type. for shallow forks, simply set or defer the value
    # depending on the current state. for deep forks, reverse associations
    # e.g. many-to-one, many-to-many will only be set once

    def _fork_one2one(self, target, value, field, direct, accessor, deep, cache):
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
                fork = value.fork(deep=deep, cache=cache)

            if not direct:
                fork = DeferProxy(fork)

            target._forkstate.defer_commit(accessor, fork, direct=direct)

    def _fork_foreignkey(self, target, value, field, direct, accessor, deep, cache):
        # direct foreign keys used as is (shallow) or forked (deep). for deep
        # forks, the association to the new objects will be defined on the
        # directly accessed object
        if value:
            if direct and deep:
                fork = cache.get(value)
                # create a new fork (which will update ``cache``)
                if fork is None:
                    fork = value.fork(deep=deep, cache=cache)

            # iterate over each object in the related set
            elif not direct and deep:
                fork = []
                for rel in value:
                    f = cache.get(rel)
                    if f is None:
                        f = rel.fork(deep=deep, cache=cache)
                    fork.append(f)

                fork = DeferProxy(fork)
            else:
                fork = value

            target._forkstate.defer_commit(accessor, fork, direct=direct)
        # nullable direct foreign keys can be set to None
        elif direct and field.null:
            setattr(target, accessor, None)


    # TODO add support for ``through`` model
    def _fork_many2many(self, target, value, field, direct, accessor, deep, cache):
        if not value:
            return

        if not deep:
            fork = value
        else:
            fork = []
            for rel in value:
                f = cache.get(rel)
                if f is None:
                    f = rel.fork(deep=deep, cache=cache)
                fork.append(f)

            if not direct:
                fork = DeferProxy(fork)

        target._forkstate.defer_commit(accessor, fork)

    def _fork_field(self, target, accessor, deep, commit, cache):
        """Creates a copy of the reference value for the defined ``accessor``
        (field). For deep forks, each related object is related objects must
        be created first prior to being recursed.
        """
        value, field, direct, m2m = self._get_field_value(accessor)

        if isinstance(field, models.OneToOneField):
            return self._fork_one2one(target, value, field, direct, accessor,
                deep, cache)

        if isinstance(field, models.ForeignKey):
            return self._fork_foreignkey(target, value, field, direct, accessor,
                deep, cache)

        if isinstance(field, models.ManyToManyField):
            return self._fork_many2many(target, value, field, direct, accessor,
                deep, cache)

        # non-relational field, perform a deepcopy to ensure no mutable nonsense
        setattr(target, accessor, deepcopy(value))

    def fork(self, target=None, fields=None, exclude=('pk',), deep=False, commit=False, cache=None):
        """Creates a fork of the reference object. If an object is supplied, it
        effectively gets reset relative to the reference object.
        """
        if target and not isinstance(target, self.__class__):
            raise TypeError('the object supplied must be of the same type as the reference')

        if not target:
            target = self.__class__()

        if not hasattr(target, '_forkstate'):
            # no fields are defined, so get the default ones for shallow or deep
            if not fields:
                fields = self._default_model_fields(exclude=exclude, deep=deep)

            # for the duration of the reset, each object's state is tracked via
            # the a ForkState object. this is primarily necessary to track
            # deferred commits of related objects
            target._forkstate = ForkState(parent=self, fields=fields, exclude=exclude)

        elif target._forkstate.has_deferreds:
            target._forkstate.clear_commits()

        target._forkstate.deep = deep

        # for every call, keep track of the reference and the object (fork).
        # this is used for recursive calls to related objects. this ensures
        # relationships that follow back up the tree are caught and are merely
        # referenced rather than traversed again.
        if not cache:
            cache = ForkCache()

        cache.add(self, target)

        # iterate over each field and fork it!. nested calls will not commit,
        # until the recursion has finished
        for accessor in fields:
            self._fork_field(target, accessor, deep=deep, commit=False, cache=cache)

        if commit:
            target.commit()

        return target

    def _diff_field(self, target, accessor, deep):
        "Returns the field's value of ``target`` if different form ``reference``."
        val1, field, direct, m2m = self._get_field_value(accessor)
        val2 = target._get_field_value(accessor)[0]

        # get the diff for m2m or reverse foreign keys
        if m2m or not direct and not isinstance(field, models.OneToOneField):
            if self._diff_queryset(val1, val2) is not None:
                return {accessor: list(val2)}
        # direct foreign keys and one-to-one
        elif deep and (isinstance(field, models.ForeignKey) or isinstance(field, models.OneToOneField)):
            if val1 and val2:
                diff = val1.diff(val2)
                if diff:
                    return {accessor: diff}
        elif val1 != val2:
            return {accessor: val2}
        return {}

    def _diff_queryset(self, qs1, qs2):
        "Compares two QuerySets by their primary keys."
        # if they point to a related manager, perform the lookup and compare
        # the primary keys
        if qs1 and qs2:
            pks1 = qs1.values_list('pk', flat=True)
            pks2 = qs2.values_list('pk', flat=True)
            if set(pks1) != set(pks2):
                return qs2
        # if they are different, check to see if either one is empty
        elif qs1:
            if qs1.count(): return qs2
        elif qs2:
            if qs2.count(): return qs2

    def diff(self, target, fields=None, exclude=('pk',), deep=False):
        """Creates a diff between two model objects of the same type relative to
        ``reference``. If ``fields`` is not supplied, all local fields and many-to-many
        fields will be included. The ``pk`` field is excluded by default.
        """
        if not fields:
            fields = self._default_model_fields(exclude, deep=deep)

        diff = {}
        for accessor in fields:
            diff.update(self._diff_field(target, accessor, deep=deep))
        return diff

    @transaction.commit_on_success
    def commit(self):
        "Recursively commits direct and related objects."
        # save dependents of this object
        self._commit_direct(direct=True, deep=self._forkstate.deep)
        # depends on ``reference`` having a primary key
        self._commit_related(deep=self._forkstate.deep)

    def _commit_direct(self, direct=True, deep=False):
        """Recursively set all direct related object references to the
        reference object. Each downstream related object is saved before
        being set.

        ``direct`` should be false if it was already called
        """
        if hasattr(self, '_forkstate'):
            # get and clear to prevent infinite recursion
            deferred = self._forkstate.deferred_direct.iteritems()
            self._forkstate.deferred_direct = {}

            for accessor, value in deferred:
                setval = True
                # execute the commit cycle, but do not actually set anything
                if deep and isinstance(value, DeferProxy):
                    value = value.value
                    setval = False

                value._commit_direct(direct=direct, deep=deep)

                if setval:
                    # save the object to get a primary key
                    setattr(self, accessor, value)

            # all save triggered by a direct commit must be saved to ensure
            # potential circular references, in addition to not already having
            # a primary key
            if direct or not self.pk:
                self.save()

    def _commit_related(self, deep=False):
        if hasattr(self, '_forkstate'):
            # get and clear to prevent infinite recursion
            deferred = self._forkstate.deferred_related.iteritems()
            self._forkstate.deferred_related = {}

            for accessor, value in deferred:
                setval = True
                # execute the commit direct cycle for these related objects,
                if isinstance(value, DeferProxy):
                    value = value.value
                    setval = False

                if type(value) is list:
                    map(lambda x: x._commit_direct(direct=False, deep=deep), value)
                elif isinstance(value, ForkableModel):
                    value._commit_direct(direct=False, deep=deep)

                if setval:
                    setattr(self, accessor, value)

                # commit all related defers
                if type(value) is list:
                    map(lambda x: x._commit_related(deep=deep), value)
                elif isinstance(value, ForkableModel):
                    value._commit_related(deep=deep)

    class Meta(object):
        abstract = True

