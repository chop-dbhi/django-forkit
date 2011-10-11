from django.db import IntegrityError
from django.test import TestCase
from forkit.tests.models import Author, Post, Blog, Tag

__all__ = ('ForkModelObjectTestCase',)

class ForkModelObjectTestCase(TestCase):
    fixtures = ['test_data.json']

    def setUp(self):
        self.author = Author.objects.get(pk=1)
        self.post = Post.objects.get(pk=1)
        self.blog = Blog.objects.get(pk=1)
        self.tag = Tag.objects.get(pk=1)

    def test_shallow_fork(self):
        # Author

        fork = self.author.fork()

        self.assertEqual(fork.pk, 3)
        self.assertEqual(self.author.posts.through.objects.count(), 3)

        fork2 = self.author.fork(commit=False)

        self.assertEqual(fork2.pk, None)
        self.assertEqual(fork2._forkstate.deferred_related.keys(), ['posts'])

        fork2.commit()
        self.assertEqual(fork2.pk, 4)
        self.assertEqual(self.author.posts.through.objects.count(), 4)
        self.assertEqual(fork2._forkstate.deferred_related, {})

        # Post

        fork = self.post.fork()
        self.assertEqual(fork.pk, 2)
        # 2 self.posts X 4 authors
        self.assertEqual(self.post.authors.through.objects.count(), 8)
        self.assertEqual(self.post.tags.through.objects.count(), 6)
        self.assertEqual(Blog.objects.count(), 1)

        fork2 = self.post.fork(commit=False)
        self.assertEqual(fork2.pk, None)

        fork2.commit()
        # 3 posts X 4 authors
        self.assertEqual(self.post.authors.through.objects.count(), 12)
        self.assertEqual(self.post.tags.through.objects.count(), 9)
        self.assertEqual(Blog.objects.count(), 1)

        # Blog

        # since this gets auto-committed, and shallow forks do not include
        # direct relation forking, no author has been set.
        self.assertRaises(IntegrityError, self.blog.fork)
        fork = self.blog.fork(commit=False)

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

        fork = self.tag.fork()
        self.assertEqual(fork.pk, 4)
        # 3 posts X 4 tags
        self.assertEqual(fork.post_set.through.objects.count(), 12)

    def test_deep_fork(self):
        # Author

        fork = self.author.fork(deep=True)

        self.assertEqual(fork.pk, 3)

        # new counts
        self.assertEqual(Author.objects.count(), 4)
        self.assertEqual(Post.objects.count(), 2)
        self.assertEqual(Blog.objects.count(), 2)
        self.assertEqual(Tag.objects.count(), 6)

        # check all through relationship
        # 1 posts X 2 authors X 2
        self.assertEqual(self.author.posts.through.objects.count(), 4)
        post = self.author.posts.all()[0]
        # 2 posts X 3 tags
        self.assertEqual(post.tags.through.objects.count(), 6)

        # Post

        fork = self.post.fork(deep=True)
        self.assertEqual(fork.pk, 3)

        # new counts
        self.assertEqual(Author.objects.count(), 6)
        self.assertEqual(Post.objects.count(), 3)
        self.assertEqual(Blog.objects.count(), 3)
        self.assertEqual(Tag.objects.count(), 9)

        # 1 posts X 2 authors X 3
        self.assertEqual(self.post.authors.through.objects.count(), 6)
        self.assertEqual(self.post.tags.through.objects.count(), 9)

        # Blog

        fork = self.blog.fork(deep=True)
        self.assertEqual(fork.pk, 4)

        # Tag

        fork = self.tag.fork(deep=True)
        self.assertEqual(fork.pk, 13)
        # 3 posts X 4 tags
        self.assertEqual(fork.post_set.through.objects.count(), 15)

