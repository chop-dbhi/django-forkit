from django.test import TestCase
from forkit.tests.models import A, B, C, D

__all__ = ('ResetModelObjectTestCase',)

class ResetModelObjectTestCase(TestCase):
    def test_shallow_reset(self):
        d1 = D(title='d1')
        a1 = A(title='a1', d=d1)
        a1.save()
        b1 = B(title='b1')
        b1.save()
        c1 = C(title='c1', a=a1, b=b1)
        c1.save()

        c2 = C(title='c2')

        c1.reset(c2)

        # shallow resets will add direct relationships if one does not
        # already exist, but will not traverse them
        self.assertEqual(c1.title, c2.title)
        self.assertEqual(c2.a, a1)
        self.assertEqual(c2.b, b1)

        # give c2 a reference to a2..
        a2 = A(title='a2')
        a2.save()
        c2.a = a2
        c2.title = 'c2'
        c2.save()

        c1.reset(c2)

        # now that c2 has a2, it does not get the a1 reference, nor
        # does a2's local attributes become reset (only deep)
        self.assertEqual(c1.title, c2.title)
        self.assertEqual(c2.a, a2)
        self.assertEqual(a2.d, None)
        self.assertEqual(a2.title, 'a2')
        self.assertEqual(c2.b, b1)


    def test_deep_reset(self):
        d1 = D(title='d1')
        a1 = A(title='a1', d=d1)
        a1.save()
        b1 = B(title='b1')
        b1.save()
        c1 = C(title='c1', a=a1, b=b1)
        c1.save()

        c2 = C(title='c2')

        c1.reset(c2, deep=True)

        # shallow resets will add direct relationships if one does not
        # already exist
        self.assertEqual(c1.title, c2.title)
        self.assertEqual(c2.a, a1)
        self.assertEqual(c2.b, b1)

        # give c2 a reference to a2..
        a2 = A(title='a2')
        a2.save()
        c2.a = a2
        c2.title = 'c2'
        c2.save()

        c1.reset(c2, deep=True)

        # now that c2 has a2, it does not get the a1 reference.
        self.assertEqual(c1.title, c2.title)
        self.assertEqual(c2.a, a2)
        self.assertEqual(c2.b, b1)

        # a2 gets reset relative to a1
        self.assertEqual(a2.title, a1.title)
        self.assertEqual(a2.d, d1)
