from django.db import models
from forkit.diff import diff_model_object
from forkit.fork import fork_model_object, reset_model_object, commit_model_object

class ForkableModel(models.Model):
    "Convenience subclass which builds in the public Forkit utilities."
    def diff(self, *args, **kwargs):
        return diff_model_object(self, *args, **kwargs)

    def fork(self, *args, **kwargs):
        return fork_model_object(self, *args, **kwargs)

    def reset(self, *args, **kwargs):
        return reset_model_object(self, *args, **kwargs)

    def commit(self):
        commit_model_object(self)

    class Meta(object):
        abstract = True

