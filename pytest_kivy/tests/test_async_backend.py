import os
import pytest

event_loop = os.environ.get('KIVY_EVENTLOOP', None)
lib_installed = os.environ.get('KIVY_EVENTLOOP_TEST_INSTALLED', event_loop)
if lib_installed == 'asyncio' or lib_installed is None:
    pytestmark = pytest.mark.asyncio
else:
    pytestmark = pytest.mark.trio


def button_app():
    from kivy.app import App
    from kivy.uix.togglebutton import ToggleButton

    class TestApp(App):
        def build(self):
            return ToggleButton(text='Hello, World!')

    return TestApp()


async def assert_app_working(app):
    root = app.app.root
    assert root.text == 'Hello, World!'
    assert root.state == 'normal'

    async for _ in app.do_touch_down_up(widget=root, widget_jitter=True):
        pass

    assert root.state == 'down'


@pytest.mark.skipif(lib_installed != 'trio', reason='Need trio installed')
async def test_button_app_trio(trio_kivy_app):
    await trio_kivy_app(button_app)
    await assert_app_working(trio_kivy_app)


@pytest.mark.skipif(
    lib_installed != 'asyncio', reason='Need asyncio installed')
async def test_button_app_asyncio(asyncio_kivy_app):
    await asyncio_kivy_app(button_app)
    await assert_app_working(asyncio_kivy_app)


@pytest.mark.skipif(
    lib_installed != event_loop, reason='Installed must match event loop')
async def test_button_app_async(async_kivy_app):
    await async_kivy_app(button_app)
    await assert_app_working(async_kivy_app)
