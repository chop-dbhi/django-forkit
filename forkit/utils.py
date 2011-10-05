from django.db import models
from django.db.models import related

class DeferProxy(object):
    def __init__(self, value):
        self.value = value

    def __repr__(self):
        return '<DeferProxy: "{0}">'.format(repr(self.value))

class ForkState(object):
    """Encapulates all state of a forked model object.

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


def _get_field_by_accessor(instance, accessor):
    """Extends the model ``Options.get_field_by_name`` to look up reverse
    relationships by their accessor name. This gets cached on the first
    lookup.

    The cache will only be needed when the ``related_name`` attribute has
    not been set for reverse relationships.
    """
    try:
        field, model, direct, m2m = instance._meta.get_field_by_name(accessor)

        if isinstance(field, related.RelatedObject):
            field = field.field
    # if this occurs, try related object accessor
    except models.FieldDoesNotExist, e:
        # check to see if this cache has been set
        if not hasattr(instance._meta, 'related_objects_by_accessor'):
            cache = {}

            # reverse foreign key and many-to-many rels
            related_objects = (
                instance._meta.get_all_related_objects() +
                instance._meta.get_all_related_many_to_many_objects()
            )

            for rel in iter(related_objects):
                cache[rel.get_accessor_name()] = rel

            instance._meta.related_objects_by_accessor = cache

        rel = instance._meta.related_objects_by_accessor.get(accessor, None)

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

def _get_field_value(instance, accessor):
    """Simple helper that returns the model's data value and catches
    non-existent related object lookups.
    """
    field, direct, m2m = _get_field_by_accessor(instance, accessor)

    value = None
    # attempt to retrieve deferred values first, since they will be
    # the value once comitted. these will never contain non-relational
    # fields
    if hasattr(instance, '_forkstate') and instance._forkstate.has_deferreds:
        if m2m:
            value = instance._forkstate.get_deferred(accessor, direct=False)
        else:
            value = instance._forkstate.get_deferred(accessor, direct=direct)
        if value and isinstance(value, DeferProxy):
            value = value.value

    # deferred relations can never be a NoneType
    if value is None:
        try:
            value = getattr(instance, accessor)
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

def _default_model_fields(instance, exclude=('pk',), deep=False):
    "Aggregates the default set of fields for creating an object fork."
    if not exclude:
        exclude = []
    # handle this special case..
    else:
        exclude = list(exclude)
        if 'pk' in exclude:
            exclude.remove('pk')
            exclude.append(instance._meta.pk.name)

    fields = (
        [f.name for f in instance._meta.fields + instance._meta.many_to_many] +
        [r.get_accessor_name() for r in instance._meta.get_all_related_many_to_many_objects()]
    )

    if deep:
        fields += [r.get_accessor_name() for r in instance._meta.get_all_related_objects()]

    return set(fields) - set(exclude)

