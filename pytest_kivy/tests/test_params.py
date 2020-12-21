import pytest
import os

lib_installed = os.environ.get('KIVY_EVENTLOOP_TEST_INSTALLED', None)
event_loop = os.environ.get('KIVY_EVENTLOOP', 'asyncio')
if lib_installed is not None and lib_installed != event_loop:
    pytestmark = pytest.mark.skip(
        'Tests are run only when event loop matches async library installed')
elif event_loop == 'asyncio':
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


async def test_app_call_cls(async_kivy_app):
    await async_kivy_app(button_app)
    await assert_app_working(async_kivy_app)


@pytest.mark.parametrize(
    'async_kivy_app', [{'app_cls': button_app}], indirect=True)
async def test_app_param_cls(async_kivy_app):
    await assert_app_working(async_kivy_app)


@pytest.mark.parametrize(
    'async_kivy_app', [{'kwargs': {'height': 400}}], indirect=True)
async def test_app_param_height(async_kivy_app):
    await async_kivy_app(button_app)
    await assert_app_working(async_kivy_app)
    assert async_kivy_app.app.root.height == 400
