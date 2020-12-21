import pytest
import os

lib_installed = os.environ.get('KIVY_EVENTLOOP_TEST_INSTALLED', None)
event_loop = os.environ.get('KIVY_EVENTLOOP', None)
pytestmark = pytest.mark.skipif(
    lib_installed != event_loop,
    reason='Tests are run only when event loop matches async library installed'
)


async def test_touch_down_up(async_kivy_app):
    def button_app():
        from kivy.app import App
        from kivy.uix.togglebutton import ToggleButton

        class TestApp(App):
            def build(self):
                return ToggleButton(text='Hello, World!')

        return TestApp()

    await async_kivy_app(button_app)

    root = async_kivy_app.app.root
    assert root.text == 'Hello, World!'
    assert root.state == 'normal'

    async for _ in async_kivy_app.do_touch_down_up(
            widget=root, widget_jitter=True):
        pass

    assert root.state == 'down'


@pytest.mark.parametrize(
    'async_kivy_app', [{'kwargs': {'height': 200, 'width': 200}}],
    indirect=True)
async def test_drag_scroll_view_pixels(async_kivy_app):
    def create_app():
        from kivy.app import App
        from kivy.lang import Builder
        from textwrap import dedent

        kv = '''
        ScrollView:
            scroll_type: ['bars']
            bar_width: '15dp'
            BoxLayout:
                width: 400
                size_hint_x: None
                Widget:
                    canvas:
                        Color:
                            rgba: 1, 0, 0, 1
                        Rectangle:
                            pos: self.pos
                            size: self.size
                Widget:
                    canvas:
                        Color:
                            rgba: 0, 1, 0, 1
                        Rectangle:
                            pos: self.pos
                            size: self.size
        '''

        class TestApp(App):
            def build(self):
                return Builder.load_string(dedent(kv))

        return TestApp()

    await async_kivy_app(create_app)

    root = async_kivy_app.app.root
    (r, g, b, a), = async_kivy_app.get_widget_pos_pixel(root, [(100, 100)])
    assert r == 255
    assert not g
    assert not b
    assert a == 255

    # drag scrollview to show second widget
    async for _ in async_kivy_app.do_touch_drag(pos=(5, 7), dx=185):
        pass

    (r, g, b, a), = async_kivy_app.get_widget_pos_pixel(root, [(100, 100)])
    assert not r
    assert g == 255
    assert not b
    assert a == 255


async def test_text_app(async_kivy_app):
    def create_app():
        from kivy.app import App
        from kivy.uix.textinput import TextInput

        class TestApp(App):
            def build(self):
                return TextInput()

        return TestApp()

    await async_kivy_app(create_app)
    root = async_kivy_app.app.root

    assert root.text == ''

    # activate widget
    async for state, touch_pos in async_kivy_app.do_touch_down_up(widget=root):
        pass

    async for state, value in async_kivy_app.do_keyboard_key(
            key='A', num_press=4):
        pass
    async for state, value in async_kivy_app.do_keyboard_key(
            key='q', num_press=3):
        pass

    assert root.text == 'AAAAqqq'
