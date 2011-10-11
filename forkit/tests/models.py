from django.db import models
from forkit.models import ForkableModel

class Tag(ForkableModel):
    name = models.CharField(max_length=30)

    def __unicode__(self):
        return u'{0}'.format(self.name)

class Author(ForkableModel):
    first_name = models.CharField(max_length=30)
    last_name = models.CharField(max_length=30)

    def __unicode__(self):
        return u'{0} {1}'.format(self.first_name, self.last_name)


class Blog(ForkableModel):
    name = models.CharField(max_length=50)
    author = models.OneToOneField(Author)

    def __unicode__(self):
        return u'{0}'.format(self.name)


class Post(ForkableModel):
    title = models.CharField(max_length=50)
    # intentionally left off the related_name attr
    blog = models.ForeignKey(Blog)
    authors = models.ManyToManyField(Author, related_name='posts')
    # intentionally left off the related_name attr
    tags = models.ManyToManyField(Tag)

    def __unicode__(self):
        return u'{0}'.format(self.title)


class A(ForkableModel):
    title = models.CharField(max_length=50)
    d = models.ForeignKey('D', null=True)

    def __unicode__(self):
        return u'{0}'.format(self.title)


class B(ForkableModel):
    title = models.CharField(max_length=50)

    def __unicode__(self):
        return u'{0}'.format(self.title)


class C(ForkableModel):
    title = models.CharField(max_length=50)
    a = models.ForeignKey(A, null=True)
    b = models.ForeignKey(B, null=True)

    def __unicode__(self):
        return u'{0}'.format(self.title)


class D(ForkableModel):
    title = models.CharField(max_length=50)

    def __unicode__(self):
        return u'{0}'.format(self.title)

