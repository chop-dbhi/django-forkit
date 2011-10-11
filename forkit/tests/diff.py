from django.test import TestCase
from forkit.tests.models import Author, Post, Blog, Tag, C

__all__ = ('DiffModelObjectTestCase',)

class DiffModelObjectTestCase(TestCase):
    fixtures = ['test_data.json']

    def setUp(self):
        self.author = Author.objects.get(pk=1)
        self.post = Post.objects.get(pk=1)
        self.blog = Blog.objects.get(pk=1)
        self.tag = Tag.objects.get(pk=1)

    def test_empty_shallow_diff(self):
        diff = self.author.diff(Author())
        self.assertEqual(diff, {
            'first_name': '',
            'last_name': '',
            'posts': [],
        })

        diff = self.blog.diff(Blog())
        self.assertEqual(diff, {
            'name': '',
            'author': None,
        })

        diff = self.post.diff(Post())
        self.assertEqual(diff, {
            'blog': None,
            'authors': [],
            'tags': [],
            'title': '',
        })

        diff = self.tag.diff(Tag())
        self.assertEqual(diff, {
            'name': '',
            'post_set': [],
        })

    def test_fork_shallow_diff(self):
        # even without the commit, the diff is clean. related objects are
        # compared against the _related dict

        fork = self.author.fork(commit=False)
        diff = fork.diff(self.author)
        self.assertEqual(diff, {})

        fork = self.post.fork(commit=False)
        diff = fork.diff(self.post)
        self.assertEqual(diff, {})

        # since Author is a OneToOneField and this is not a deep fork, it
        # still does not have a value
        fork = self.blog.fork(commit=False)
        diff = fork.diff(self.blog)
        self.assertEqual(diff, {
            'author': self.author
        })

        diff = self.blog.diff(fork)
        self.assertEqual(diff, {
            'author': None
        })

        fork = self.tag.fork(commit=False)
        diff = self.tag.diff(fork)
        self.assertEqual(diff, {})

    def test_deep_diff(self):
        # only simple data models are currently supported
        c = C.objects.get(pk=1)

        # need to commit, since lists are not yet handled..
        fork = c.fork(commit=True, deep=True)
        diff = c.diff(fork, deep=True)
        self.assertEqual(diff, {})

        fork.b.title = 'foobar'
        self.assertEqual(c.diff(fork, deep=True), {
            'b': {
                'title': 'foobar',
            }
        })
