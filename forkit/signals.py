from django.dispatch import Signal

pre_reset = Signal(providing_args=('reference', 'instance', 'config'))
post_reset = Signal(providing_args=('reference', 'instance'))

pre_fork = Signal(providing_args=('reference', 'instance', 'config'))
post_fork = Signal(providing_args=('reference', 'instance'))

pre_diff = Signal(providing_args=('reference', 'instance', 'config'))
post_diff = Signal(providing_args=('reference', 'instance', 'diff'))

pre_commit = Signal(providing_args=('reference', 'instance'))
post_commit = Signal(providing_args=('reference', 'instance'))
