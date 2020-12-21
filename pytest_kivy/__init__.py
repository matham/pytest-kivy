"""pytest-trio
==============

Provides pytest fixtures to more easily test Kivy GUI apps.
"""

import pytest

pytest.register_assert_rewrite("pytest_kivy.resolver")
pytest.register_assert_rewrite("pytest_kivy.app")

__version__ = '0.1.0.dev0'
