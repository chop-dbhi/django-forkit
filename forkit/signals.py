from django.dispatch import Signal

pre_reset = Signal(providing_args=('parent', 'instance', 'config'))
post_reset = Signal(providing_args=('parent', 'instance'))

pre_fork = Signal(providing_args=('parent', 'instance', 'config'))
post_fork = Signal(providing_args=('parent', 'instance'))

pre_diff = Signal(providing_args=('parent', 'instance', 'config'))
post_diff = Signal(providing_args=('parent', 'instance', 'diff'))

pre_commit = Signal(providing_args=('parent', 'instance'))
post_commit = Signal(providing_args=('parent', 'instance'))
