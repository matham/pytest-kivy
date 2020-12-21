from setuptools import setup, find_packages
from io import open
from os.path import dirname, join, abspath

here = abspath(dirname(__file__))

# __version__ is imported by exec, but help linter not complain
__version__ = None
with open(join(here, 'pytest_kivy', '_version.py'), encoding="utf-8") as f:
    exec(f.read())


with open(join(here, 'README.rst'), encoding='utf-8') as f:
    long_description = f.read()

URL = 'https://github.com/matham/pytest-kivy'

setup(
    name='pytest-kivy',
    version=__version__,
    author='Matthew Einhorn',
    author_email='moiein2000@gmail.com',
    license='MIT',
    description='Kivy GUI tests fixtures using pytest',
    long_description=long_description,
    url=URL,
    classifiers=[
        'Development Status :: 4 - Beta',
        'License :: OSI Approved :: MIT License',
        "Programming Language :: Python :: 3 :: Only",
        "Topic :: Software Development :: Testing",
        "Framework :: Pytest",
    ],
    packages=find_packages(),
    entry_points={"pytest11": ["kivy = pytest_kivy.plugin"]},
    project_urls={
        'Bug Reports': URL + '/issues',
        'Source': URL,
    },
)
