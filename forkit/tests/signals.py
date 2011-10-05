from django.test import TestCase
from forkit import utils, signals
from forkit.tests.models import Author, Post, Blog, Tag

__all__ = ('SignalsTestCase',)

# receivers
def author_config(sender, config, **kwargs):
    config['fields'] = ['first_name', 'posts']

def post_config(sender, config, **kwargs):
    config['fields'] = ['title']

class SignalsTestCase(TestCase):
    fixtures = ['test_data.json']

    def setUp(self):
        self.author = Author.objects.get(pk=1)
        self.post = Post.objects.get(pk=1)
        self.blog = Blog.objects.get(pk=1)
        self.tag = Tag.objects.get(pk=1)

    def test_shallow_signal(self):
        signals.pre_fork.connect(author_config, sender=Author)

        fork = self.author.fork()
        self.assertEqual(self.author.diff(fork), {
            'last_name': ''
        });

        signals.pre_fork.disconnect(author_config)

    def test_deep_signal(self):
        # before signal is connected.. complete deep fork
        fork = self.author.fork(commit=False, deep=True)

        post0 = utils._get_field_value(fork, 'posts')[0][0]
        self.assertEqual(post0.title, 'Django Tip: Descriptors')

        blog0 = utils._get_field_value(post0, 'blog')[0]
        self.assertTrue(isinstance(blog0, Blog))

        # connect the post signal to limit the fields..
        signals.pre_fork.connect(post_config, sender=Post)

        fork = self.author.fork(commit=False, deep=True)

        post0 = utils._get_field_value(fork, 'posts')[0][0]
        self.assertEqual(post0.title, 'Django Tip: Descriptors')

        blog0 = utils._get_field_value(post0, 'blog')[0]
        # odd usage of _get_field_value, but it works..
        self.assertEqual(blog0, None)

        signals.pre_fork.disconnect(post_config)

