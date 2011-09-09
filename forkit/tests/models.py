from django.db import models
from django.db import IntegrityError
from django.test import TestCase
from forkit.models import ForkableModel

__all__ = ('ForkableModelTestCase',)

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


class B(ForkableModel):
    title = models.CharField(max_length=50)


class C(ForkableModel):
    title = models.CharField(max_length=50)
    a = models.ForeignKey(A, null=True)
    b = models.ForeignKey(B, null=True)


class ForkableModelTestCase(TestCase):
    fixtures = ['test_data.json']

    def test_accessor_cache(self):
        author = Author.objects.get(pk=1)
        post = Post.objects.get(pk=1)
        blog = Blog.objects.get(pk=1)
        tag = Tag.objects.get(pk=1)

        author._meta.get_field_by_accessor('posts')
        author._meta.get_field_by_accessor('blog')
        # the forker has not been populated with the cache because it
        # did not need it.
        self.assertFalse(hasattr(author._meta, 'related_objects_by_accessor'))

        post._meta.get_field_by_accessor('authors')
        post._meta.get_field_by_accessor('blog')
        post._meta.get_field_by_accessor('tags')
        self.assertFalse(hasattr(post._meta, 'related_objects_by_accessor'))

        blog._meta.get_field_by_accessor('author')
        # intentionally left off a related_name
        blog._meta.get_field_by_accessor('post_set')
        # the cache was created for the ``post_set`` accessor
        self.assertEqual(blog._meta.related_objects_by_accessor.keys(), ['post_set'])

        # reverse many-to-many without a related_name can also be looked up by
        # their model name
        tag._meta.get_field_by_accessor('post')
        # no cache will be created
        self.assertFalse(hasattr(tag._meta, 'related_objects_by_accessor'))

    def test_field_value(self):
        author = Author.objects.get(pk=1)
        post = Post.objects.get(pk=1)
        blog = Blog.objects.get(pk=1)
        tag = Tag.objects.get(pk=1)

        self.assertEqual(author._get_field_value('first_name')[0], 'Byron')
        # returns a queryset, compare the querysets
        author_posts = author._get_field_value('posts')[0]
        self.assertEqual(author._diff_queryset(author_posts, Post.objects.all()), None)
        # one-to-ones are simple, the instance if returned directly
        self.assertEqual(author._get_field_value('blog')[0], blog)

        # direct foreign key, same as one-to-one
        self.assertEqual(post._get_field_value('blog')[0], blog)
        # direct many-to-many, behaves the same as reverse foreign keys
        post_authors = post._get_field_value('authors')[0]
        self.assertEqual(post._diff_queryset(post_authors, Author.objects.all()), None)
        # direct many-to-many, behaves the same as reverse foreign keys
        post_tags = post._get_field_value('tags')[0]
        self.assertEqual(post._diff_queryset(post_tags, Tag.objects.all()), None)

        self.assertEqual(blog._get_field_value('author')[0], author)
        blog_posts = blog._get_field_value('post_set')[0]
        self.assertEqual(blog._diff_queryset(blog_posts, Post.objects.all()), None)

        tag_posts = tag._get_field_value('post_set')[0]
        self.assertEqual(blog._diff_queryset(tag_posts, Post.objects.all()), None)

    def test_shallow_default_fields(self):
        author = Author()
        post = Post()
        blog = Blog()
        tag = Tag()

        self.assertEqual(author._default_model_fields(),
            set(['first_name', 'last_name', 'posts']))

        self.assertEqual(post._default_model_fields(),
            set(['blog', 'authors', 'tags', 'title']))

        self.assertEqual(blog._default_model_fields(),
            set(['name', 'author']))

        self.assertEqual(tag._default_model_fields(),
            set(['name', 'post_set']))

    def test_deep_default_fields(self):
        author = Author()
        post = Post()
        blog = Blog()
        tag = Tag()

        self.assertEqual(author._default_model_fields(deep=True),
            set(['first_name', 'last_name', 'posts', 'blog']))

        self.assertEqual(post._default_model_fields(deep=True),
            set(['blog', 'authors', 'tags', 'title']))

        self.assertEqual(blog._default_model_fields(deep=True),
            set(['name', 'author', 'post_set']))

        self.assertEqual(tag._default_model_fields(deep=True),
            set(['name', 'post_set']))

    def test_shallow_diff(self):
        author = Author.objects.get(pk=1)
        post = Post.objects.get(pk=1)
        blog = Blog.objects.get(pk=1)
        tag = Tag.objects.get(pk=1)

        self.assertEqual(author.diff(Author()), {
            'first_name': '',
            'last_name': '',
            'posts': [],
        })

        fork = author.fork(commit=False)
        # even without the commit, the diff is clean. related objects are
        # compared against the _deferred_related dict
        self.assertEqual(fork.diff(author), {})
        self.assertEqual(author.diff(fork), {})

        self.assertEqual(post.diff(Post()), {
            'blog': None,
            'authors': [],
            'tags': [],
            'title': '',
        })

        fork = post.fork(commit=False)
        # even without the commit, the diff is clean. related objects are
        # compared against the _deferred_related dict
        self.assertEqual(fork.diff(post), {})
        self.assertEqual(post.diff(fork), {})

        self.assertEqual(blog.diff(Blog()), {
            'name': '',
            'author': None,
        })

        fork = blog.fork(commit=False)
        # since Author is a OneToOneField and this is not a deep fork, it
        # still does not have a value
        self.assertEqual(fork.diff(blog), {
            'author': author
        })
        self.assertEqual(blog.diff(fork), {
            'author': None
        })


        self.assertEqual(tag.diff(Tag()), {
            'name': '',
            'post_set': [],
        })

        fork = tag.fork(commit=False)
        # since Author is a OneToOneField and this is not a deep fork, it
        # still does not have a value
        self.assertEqual(fork.diff(tag), {})
        self.assertEqual(tag.diff(fork), {})

    def test_shallow_fork(self):
        # Author

        author = Author.objects.get(pk=1)
        fork = author.fork(commit=True)

        self.assertEqual(fork.pk, 3)
        self.assertEqual(author.posts.through.objects.count(), 3)

        fork2 = author.fork(commit=False)

        self.assertEqual(fork2.pk, None)
        self.assertEqual(fork2._forkstate.deferred_related.keys(), ['posts'])

        fork2.commit()
        self.assertEqual(fork2.pk, 4)
        self.assertEqual(author.posts.through.objects.count(), 4)
        self.assertEqual(fork2._forkstate.deferred_related, {})

        # Post

        post = Post.objects.get(pk=1)
        fork = post.fork(commit=True)
        self.assertEqual(fork.pk, 2)
        # 2 posts X 4 authors
        self.assertEqual(post.authors.through.objects.count(), 8)
        self.assertEqual(post.tags.through.objects.count(), 6)
        self.assertEqual(Blog.objects.count(), 1)

        fork2 = post.fork(commit=False)
        self.assertEqual(fork2.pk, None)

        fork2.commit()
        # 3 posts X 4 authors
        self.assertEqual(post.authors.through.objects.count(), 12)
        self.assertEqual(post.tags.through.objects.count(), 9)
        self.assertEqual(Blog.objects.count(), 1)

        # Blog

        blog = Blog.objects.get(pk=1)
        # since this gets auto-committed, and shallow forks do not include
        # direct relation forking, no author has been set.
        self.assertRaises(IntegrityError, blog.fork, commit=True)
        fork = blog.fork(commit=False)

        fork_author = Author()
        fork_author.save()
        fork.author = fork_author
        fork.commit()

        self.assertEqual(fork.pk, 2)

        # test fork when one-to-one is not yet
        blog = Blog()
        fork = blog.fork(commit=False)
        self.assertEqual(fork.diff(blog), {})

        # Tag

        tag = Tag.objects.get(pk=1)
        fork = tag.fork(commit=True)
        self.assertEqual(fork.pk, 4)
        # 3 posts X 4 tags
        self.assertEqual(fork.post_set.through.objects.count(), 12)

    def test_deep_fork(self):
        # Author

        author = Author.objects.get(pk=1)
        fork = author.fork(commit=True, deep=True)

        self.assertEqual(fork.pk, 3)

        # new counts
        self.assertEqual(Author.objects.count(), 4)
        self.assertEqual(Post.objects.count(), 2)
        self.assertEqual(Blog.objects.count(), 2)
        self.assertEqual(Tag.objects.count(), 6)

        # check all through relationship
        # 1 posts X 2 authors X 2
        self.assertEqual(author.posts.through.objects.count(), 4)
        post = author.posts.all()[0]
        # 2 posts X 3 tags
        self.assertEqual(post.tags.through.objects.count(), 6)

        # Post

        post = Post.objects.get(pk=1)
        fork = post.fork(commit=True, deep=True)
        self.assertEqual(fork.pk, 3)

        # new counts
        self.assertEqual(Author.objects.count(), 6)
        self.assertEqual(Post.objects.count(), 3)
        self.assertEqual(Blog.objects.count(), 3)
        self.assertEqual(Tag.objects.count(), 9)

        # 1 posts X 2 authors X 3
        self.assertEqual(post.authors.through.objects.count(), 6)
        self.assertEqual(post.tags.through.objects.count(), 9)

        # Blog

        blog = Blog.objects.get(pk=1)
        fork = blog.fork(commit=True, deep=True)
        self.assertEqual(fork.pk, 4)

        # Tag

        tag = Tag.objects.get(pk=1)
        fork = tag.fork(commit=True, deep=True)
        self.assertEqual(fork.pk, 13)
        # 3 posts X 4 tags
        self.assertEqual(fork.post_set.through.objects.count(), 15)

    def test_deep_diff(self):
        # only simple data models are currently supported
        c = C.objects.get(pk=1)
        fork = c.fork(commit=True, deep=True)
        self.assertEqual(c.diff(fork, deep=True), {})

        fork.b.title = 'foobar'

        self.assertEqual(c.diff(fork, deep=True), {
            'b': {
                'title': 'foobar',
            }
        })
