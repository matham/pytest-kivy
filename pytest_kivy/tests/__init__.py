import pytest
import os

__all__ = ('get_pytest_async_mark', )


def get_pytest_async_mark():
    lib_installed = os.environ.get('KIVY_EVENTLOOP_TEST_INSTALLED', None)
    event_loop = os.environ.get('KIVY_EVENTLOOP', 'asyncio')
    if lib_installed is not None and lib_installed != event_loop:
        pytestmark = pytest.mark.skip(
            'Tests are run only when event loop matches async library '
            'installed')
    elif event_loop == 'asyncio':
        pytestmark = pytest.mark.asyncio
    else:
        pytestmark = pytest.mark.trio

    return pytestmark
