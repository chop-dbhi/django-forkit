DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': 'forkit.db',
    }
}

INSTALLED_APPS = (
    'forkit',
    'forkit.tests'
)

COVERAGE_MODULES = (
    'forkit.diff',
    'forkit.fork',
    'forkit.reset',
    'forkit.commit',
    'forkit.utils',
)

TEST_RUNNER = 'forkit.tests.coverage_test.CoverageTestRunner'
