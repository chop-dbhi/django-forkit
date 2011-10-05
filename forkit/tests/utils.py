from django.test import TestCase
from forkit import utils, diff
from forkit.tests.models import Author, Post, Blog, Tag

__all__ = ('UtilsTestCase',)

class UtilsTestCase(TestCase):
    fixtures = ['test_data.json']

    def setUp(self):
        self.author = Author.objects.get(pk=1)
        self.post = Post.objects.get(pk=1)
        self.blog = Blog.objects.get(pk=1)
        self.tag = Tag.objects.get(pk=1)

    def test_accessor_cache(self):
        utils._get_field_by_accessor(self.author, 'posts')
        utils._get_field_by_accessor(self.author, 'blog')

        utils._get_field_by_accessor(self.post, 'authors')
        utils._get_field_by_accessor(self.post, 'blog')
        utils._get_field_by_accessor(self.post, 'tags')

        utils._get_field_by_accessor(self.blog, 'author')
        # intentionally left off a related_name
        utils._get_field_by_accessor(self.blog, 'post_set')
        # the cache was created for the ``post_set`` accessor
        self.assertEqual(self.blog._meta.related_objects_by_accessor.keys(), ['post_set'])

        # reverse many-to-many without a related_name can also be looked up by
        # their model name
        utils._get_field_by_accessor(self.tag, 'post')

    def test_field_value(self):
        self.assertEqual(utils._get_field_value(self.author, 'first_name')[0], 'Byron')
        # returns a queryset, compare the querysets
        author_posts = utils._get_field_value(self.author, 'posts')[0]
        self.assertEqual(diff._diff_queryset(self.author, author_posts, Post.objects.all()), None)
        # one-to-ones are simple, the instance if returned directly
        self.assertEqual(utils._get_field_value(self.author, 'blog')[0], self.blog)

        # direct foreign key, same as one-to-one
        self.assertEqual(utils._get_field_value(self.post, 'blog')[0], self.blog)
        # direct many-to-many, behaves the same as reverse foreign keys
        post_authors = utils._get_field_value(self.post, 'authors')[0]
        self.assertEqual(diff._diff_queryset(self.post, post_authors, Author.objects.all()), None)
        # direct many-to-many, behaves the same as reverse foreign keys
        post_tags = utils._get_field_value(self.post, 'tags')[0]
        self.assertEqual(diff._diff_queryset(self.post, post_tags, Tag.objects.all()), None)

        self.assertEqual(utils._get_field_value(self.blog, 'author')[0], self.author)
        blog_posts = utils._get_field_value(self.blog, 'post_set')[0]
        self.assertEqual(diff._diff_queryset(self.blog, blog_posts, Post.objects.all()), None)

        tag_posts = utils._get_field_value(self.tag, 'post_set')[0]
        self.assertEqual(diff._diff_queryset(self.blog, tag_posts, Post.objects.all()), None)

    def test_shallow_default_fields(self):
        author = Author()
        post = Post()
        blog = Blog()
        tag = Tag()

        self.assertEqual(utils._default_model_fields(author),
            set(['first_name', 'last_name', 'posts']))

        self.assertEqual(utils._default_model_fields(post),
            set(['blog', 'authors', 'tags', 'title']))

        self.assertEqual(utils._default_model_fields(blog),
            set(['name', 'author']))

        self.assertEqual(utils._default_model_fields(tag),
            set(['name', 'post_set']))

    def test_deep_default_fields(self):
        author = Author()
        post = Post()
        blog = Blog()
        tag = Tag()

        self.assertEqual(utils._default_model_fields(author, deep=True),
            set(['first_name', 'last_name', 'posts', 'blog']))

        self.assertEqual(utils._default_model_fields(post, deep=True),
            set(['blog', 'authors', 'tags', 'title']))

        self.assertEqual(utils._default_model_fields(blog, deep=True),
            set(['name', 'author', 'post_set']))

        self.assertEqual(utils._default_model_fields(tag, deep=True),
            set(['name', 'post_set']))

