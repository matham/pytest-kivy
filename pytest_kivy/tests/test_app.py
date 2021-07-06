import pytest
from math import isclose
from functools import partial

from pytest_kivy.tests import get_pytest_async_mark
from pytest_kivy.tools import exhaust

pytestmark = get_pytest_async_mark()


class StartupException(Exception):
    pass


def create_app():
    from kivy.app import App
    from kivy.uix.widget import Widget

    class TestApp(App):
        def build(self):
            return Widget()

        def on_start(self):
            raise StartupException

    return TestApp()


@pytest.mark.xfail(raises=StartupException, strict=True)
async def test_exception_start_app(async_kivy_app):
    await async_kivy_app(create_app)


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

    await exhaust(
        async_kivy_app.do_touch_down_up(widget=root, widget_jitter=True))

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


def create_text_app(text=''):
    from kivy.app import App
    from kivy.uix.textinput import TextInput

    class TestApp(App):
        def build(self):
            return TextInput(text=text)

    return TestApp()


async def test_text_app(async_kivy_app):
    await async_kivy_app(create_text_app)
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


async def test_replace_text_app(async_kivy_app):
    await async_kivy_app(partial(create_text_app, text='hello'))

    root = async_kivy_app.app.root
    assert root.text == 'hello'

    # activate it
    async for state, touch_pos in async_kivy_app.do_touch_down_up(widget=root):
        pass

    # select all
    ctrl_it = async_kivy_app.do_keyboard_key(key='lctrl', modifiers=['ctrl'])
    await ctrl_it.__anext__()  # down

    async for _ in async_kivy_app.do_keyboard_key(key='a', modifiers=['ctrl']):
        pass
    await ctrl_it.__anext__()  # up
    with pytest.raises(StopAsyncIteration):
        await ctrl_it.__anext__()

    # replace text
    for key in ['delete'] + list('new text') + ['enter']:
        async for _ in async_kivy_app.do_keyboard_key(key=key):
            pass

    assert root.text == 'new text\n'


@pytest.mark.parametrize(
    'async_kivy_app', [{'kwargs': {'height': 200, 'width': 200}}],
    indirect=True)
async def test_touch_drag_path(async_kivy_app):
    path = list(zip(range(5, 95, 5), range(20, 110, 5)))
    pos = []

    def path_app():
        from kivy.app import App
        from kivy.uix.widget import Widget

        class MyWidget(Widget):
            def on_touch_down(self, touch):
                pos.append(tuple(map(int, touch.pos)))
                return super().on_touch_down(touch)

            def on_touch_move(self, touch):
                pos.append(tuple(map(int, touch.pos)))
                return super().on_touch_move(touch)

            def on_touch_up(self, touch):
                pos.append(tuple(map(int, touch.pos)))
                return super().on_touch_up(touch)

        class TestApp(App):
            def build(self):
                return MyWidget()

        return TestApp()

    await async_kivy_app(path_app)

    async for _ in async_kivy_app.do_touch_drag_path(path):
        pass

    assert len(path) + 1 == len(pos)
    for (x1, y1), (x2, y2) in zip(pos, path + [path[-1]]):
        assert isclose(x1, x2, abs_tol=1)
        assert isclose(y1, y2, abs_tol=1)


@pytest.mark.parametrize(
    'async_kivy_app', [{'kwargs': {'height': 200, 'width': 200}}],
    indirect=True)
async def test_touch_drag_follow(async_kivy_app):
    def follow_app():
        from kivy.app import App
        from kivy.uix.widget import Widget

        class TestApp(App):
            def build(self):
                widget = Widget()
                widget.add_widget(Widget(size=(10, 10), pos=(0, 0)))
                return widget

        return TestApp()

    await async_kivy_app(follow_app)
    follow = async_kivy_app.app.root.children[0]

    x = y = None
    async for state, (x, y) in async_kivy_app.do_touch_drag_follow(
            pos=(100, 195), target_widget=follow, drag_n=5):
        if (int(x), int(y)) == (int(follow.center_x), int(follow.center_y)):
            break

        follow.x += 15
        follow.y += 10
        await async_kivy_app.wait_clock_frames(1)

    assert (int(x), int(y)) == (int(follow.center_x), int(follow.center_y))
