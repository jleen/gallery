from setuptools import setup

setup(
    name='gallery',
    version='0.1',
    packages=['gallery'],
    entry_points={
        'console_scripts': ['gallery = gallery.staticgen:staticgen'],
    },
)
