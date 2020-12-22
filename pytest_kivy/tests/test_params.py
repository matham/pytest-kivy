import pytest
from pytest_kivy.app import AsyncUnitApp
from pytest_kivy.tests import get_pytest_async_mark

pytestmark = get_pytest_async_mark()


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
    assert isinstance(async_kivy_app, AsyncUnitApp)
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


class CustomAsyncUnitApp(AsyncUnitApp):
    pass


@pytest.mark.parametrize(
    'async_kivy_app', [{'cls': CustomAsyncUnitApp}], indirect=True)
async def test_app_cls(async_kivy_app):
    assert isinstance(async_kivy_app, CustomAsyncUnitApp)
    await async_kivy_app(button_app)
    await assert_app_working(async_kivy_app)
