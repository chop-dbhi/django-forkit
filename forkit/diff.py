from django.db import models
from forkit import utils

def _diff_field(instance, target, accessor, deep):
    "Returns the field's value of ``target`` if different form ``reference``."
    val1, field, direct, m2m = utils._get_field_value(instance, accessor)
    val2 = utils._get_field_value(target, accessor)[0]

    # get the diff for m2m or reverse foreign keys
    if m2m or not direct and not isinstance(field, models.OneToOneField):
        if _diff_queryset(instance, val1, val2) is not None:
            return {accessor: list(val2)}
    # direct foreign keys and one-to-one
    elif deep and (isinstance(field, models.ForeignKey) or isinstance(field, models.OneToOneField)):
        if val1 and val2:
            diff = diff_model_object(val1, val2)
            if diff:
                return {accessor: diff}
    elif val1 != val2:
        return {accessor: val2}
    return {}

def _diff_queryset(instance, qs1, qs2):
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

def diff_model_object(instance, target, fields=None, exclude=('pk',), deep=False):
    """Creates a diff between two model objects of the same type relative to
    ``reference``. If ``fields`` is not supplied, all local fields and many-to-many
    fields will be included. The ``pk`` field is excluded by default.
    """
    if not fields:
        fields = utils._default_model_fields(instance, exclude, deep=deep)

    diff = {}
    for accessor in fields:
        diff.update(_diff_field(instance, target, accessor, deep=deep))

    return diff

