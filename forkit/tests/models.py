from django.db import models
from forkit.models import ForkableModel

class Tag(ForkableModel):
    name = models.CharField(max_length=30)


class Author(ForkableModel):
    first_name = models.CharField(max_length=30)
    last_name = models.CharField(max_length=30)


class Blog(ForkableModel):
    name = models.CharField(max_length=50)
    author = models.OneToOneField(Author)


class Post(ForkableModel):
    title = models.CharField(max_length=50)
    # intentionally left off the related_name attr
    blog = models.ForeignKey(Blog)
    authors = models.ManyToManyField(Author, related_name='posts')
    # intentionally left off the related_name attr
    tags = models.ManyToManyField(Tag)


class A(ForkableModel):
    title = models.CharField(max_length=50)
    d = models.ForeignKey('D', null=True)


class B(ForkableModel):
    title = models.CharField(max_length=50)


class C(ForkableModel):
    title = models.CharField(max_length=50)
    a = models.ForeignKey(A, null=True)
    b = models.ForeignKey(B, null=True)


class D(ForkableModel):
    title = models.CharField(max_length=50)
