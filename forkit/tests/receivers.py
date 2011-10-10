from django.dispatch import receiver
from forkit import signals

@receiver(signals.pre_reset)
def debug_pre_reset(instance, **kwargs):
    print repr(instance), 'pre-reset'

@receiver(signals.post_reset)
def debug_post_reset(instance, **kwargs):
    print repr(instance), 'post-reset'

@receiver(signals.pre_commit)
def debug_pre_commit(instance, **kwargs):
    print repr(instance), 'pre-commit'

@receiver(signals.post_commit)
def debug_post_commit(instance, **kwargs):
    print repr(instance), 'post-commit'

@receiver(signals.pre_fork)
def debug_pre_fork(instance, **kwargs):
    print repr(instance), 'pre-fork'

@receiver(signals.post_fork)
def debug_post_fork(instance, **kwargs):
    print repr(instance), 'post-fork'

@receiver(signals.pre_diff)
def debug_pre_diff(instance, **kwargs):
    print repr(instance), 'pre-diff'

@receiver(signals.post_diff)
def debug_post_diff(instance, **kwargs):
    print repr(instance), 'post-diff'
