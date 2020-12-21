"""pytest-trio
==============

Provides pytest fixtures to more easily test Kivy GUI apps.
"""
from pytest_kivy._version import __version__

import pytest

pytest.register_assert_rewrite("pytest_kivy.resolver")
pytest.register_assert_rewrite("pytest_kivy.app")
