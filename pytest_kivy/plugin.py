"""Plugin
=========

The fixtures provided by pytest-kivy.
"""
import pytest
import weakref
from typing import Tuple, Type, Optional, Callable
import gc
import logging
from os import environ

from pytest_kivy.app import AsyncUnitApp

__all__ = ('trio_kivy_app', 'asyncio_kivy_app', 'async_kivy_app')

#: NOTE: Kivy cannot be imported before or while the plugin is imported or
# configured as that leads to pytest issues.

environ['KIVY_USE_DEFAULTCONFIG'] = '1'

_async_lib = environ.get('KIVY_EVENTLOOP', 'asyncio')
if _async_lib == 'asyncio':
    @pytest.fixture
    async def _nursery():
        return None

    @pytest.fixture
    async def _event_loop(event_loop):
        return event_loop
elif _async_lib == 'trio':
    @pytest.fixture
    async def _nursery(nursery):
        return nursery

    @pytest.fixture
    async def _event_loop():
        return None
else:
    raise TypeError(f'unknown event loop {_async_lib}')


def pytest_addoption(parser):
    group = parser.getgroup("kivy")
    group.addoption(
        "--kivy-app-release",
        action="store_true",
        default=False,
        help='Whether to check after each test if the app is released and no '
             'references are kept to the app preventing it from being garbage '
             'collected.',
    )
    group.addoption(
        "--kivy-app-release-end",
        action="store_true",
        default=False,
        help='Whether to check at the end of all tests if all of the test apps'
             'were released and no references were kept to the app preventing'
             'them from being garbage collected.',
    )


@pytest.fixture(scope='session')
def _app_release_list():
    apps = []

    yield apps

    gc.collect()
    alive_apps = []
    for i, (app, request) in enumerate(apps[:-1]):
        app = app()
        request = request()
        if request is None:
            request = '<dead request>'

        if app is not None:
            alive_apps.append((app, request))
            logging.error(
                'Memory leak: failed to release app for test ' + repr(request))

    assert not alive_apps, 'Memory leak: failed to release all apps'


@pytest.fixture
def _app_release():
    app = []

    yield app

    gc.collect()

    if not app:
        return

    app, request = app[0]
    app = app()
    request = request()
    if request is None:
        request = '<dead request>'

    assert app is None, \
        f'Memory leak: failed to release app for test {request!r}'


def _get_request_config(
        request, _app_release_list, _app_release
) -> Tuple[Type[AsyncUnitApp], dict, Optional[Callable], list]:
    opts = getattr(request, 'param', {})
    cls = opts.get('cls', AsyncUnitApp)
    kwargs = opts.get('kwargs', {})
    app_cls = opts.get('app_cls', None)

    app_list = None
    if request.config.getoption("kivy_app_release"):
        app_list = _app_release
    elif request.config.getoption("kivy_app_release_end"):
        app_list = _app_release_list
    return cls, kwargs, app_cls, app_list


@pytest.fixture
async def trio_kivy_app(
        request, nursery, _app_release_list, _app_release
) -> AsyncUnitApp:
    """Fixture yielding a :class:`~pytest_kivy.app.AsyncUnitApp` using
    explicitly trio as backend for the async library.

    pytest-trio and trio must be installed, and ``trio_mode = true`` must be
    set in pytest.ini.
    """
    cls, kwargs, app_cls, app_list = _get_request_config(
        request, _app_release_list, _app_release)

    async with cls(nursery=nursery, async_lib='trio', **kwargs) as app:
        if app_list is not None:
            app_list.append((weakref.ref(app), weakref.ref(request)))

        if app_cls is not None:
            await app(app_cls)
        app.raise_startup_exception()

        yield app
        await app.wait_stop_app()


@pytest.fixture
async def asyncio_kivy_app(
        request, event_loop, _app_release_list, _app_release) -> AsyncUnitApp:
    """Fixture yielding a :class:`~pytest_kivy.app.AsyncUnitApp` using
    explicitly asyncio as backend for the async library.

    pytest-asyncio must be installed.
    """
    cls, kwargs, app_cls, app_list = _get_request_config(
        request, _app_release_list, _app_release)

    async with cls(
            event_loop=event_loop, async_lib='asyncio', **kwargs) as app:
        if app_list is not None:
            app_list.append((weakref.ref(app), weakref.ref(request)))

        if app_cls is not None:
            await app(app_cls)
        app.raise_startup_exception()

        yield app
        await app.wait_stop_app()


@pytest.fixture
async def async_kivy_app(
        request, _app_release_list, _app_release, _nursery, _event_loop
) -> AsyncUnitApp:
    """Fixture yielding a :class:`~pytest_kivy.app.AsyncUnitApp` using
    trio or asyncio as backend for the async library, depending on
    KIVY_EVENTLOOP.

    If using trio, pytest-trio and trio must be installed, and
    ``trio_mode = true`` must be set in pytest.ini. If using asyncio,
    pytest-asyncio must be installed.
    """
    cls, kwargs, app_cls, app_list = _get_request_config(
        request, _app_release_list, _app_release)

    async with cls(
            nursery=_nursery, event_loop=_event_loop, async_lib=_async_lib,
            **kwargs) as app:
        if app_list is not None:
            app_list.append((weakref.ref(app), weakref.ref(request)))

        if app_cls is not None:
            await app(app_cls)
        app.raise_startup_exception()

        yield app
        await app.wait_stop_app()
