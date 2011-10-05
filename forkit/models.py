from django.db import models
from forkit import tools

class ForkableModel(models.Model):
    "Convenience subclass which builds in the public Forkit utilities."
    def diff(self, *args, **kwargs):
        return tools.diff(self, *args, **kwargs)

    def fork(self, *args, **kwargs):
        return tools.fork(self, *args, **kwargs)

    def reset(self, *args, **kwargs):
        return tools.reset(self, *args, **kwargs)

    def commit(self):
        tools.commit(self)

    class Meta(object):
        abstract = True

