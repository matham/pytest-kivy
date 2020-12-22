import pytest
from pytest_kivy.tests import get_pytest_async_mark
from pytest_kivy.resolver import ResolverNotFound

pytestmark = get_pytest_async_mark()

kv = '''
BoxLayout:
    BoxLayout:
        id: a1
        name: 'a1'
        BoxLayout:
            id: a11
            name: 'a11'
        BoxLayout:
            id: a12
            Widget:
                id: widget
                name: 'widget'
    BoxLayout:
        id: a2
        name: 'a2'
        Label:
            id: label
            text: "hello"
        Button:
            id: button
            text: "hello"
        BoxLayout:
            id: a21
            name: 'a21'
        BoxLayout:
            id: a22
'''


def create_kv_app():
    from kivy.app import App
    from kivy.lang import Builder

    class TestApp(App):
        def build(self):
            return Builder.load_string(kv)

    return TestApp()


async def test_resolve_base_window(async_kivy_app):
    await async_kivy_app(create_kv_app)
    from kivy.core.window import Window

    root_resolver = async_kivy_app.resolve_widget()
    assert root_resolver() is Window


async def test_resolve_down(async_kivy_app):
    await async_kivy_app(create_kv_app)
    ids = async_kivy_app.app.root.ids

    for name in ('a1', 'a11', 'widget', 'a21'):
        matched = async_kivy_app.resolve_widget().down(name=name)()
        assert matched is ids[name].__self__

    with pytest.raises(ResolverNotFound):
        async_kivy_app.resolve_widget().down(name='something')


async def test_resolve_down_func(async_kivy_app):
    await async_kivy_app(create_kv_app)
    ids = async_kivy_app.app.root.ids

    for cls_name in ['Widget', 'Label', 'Button']:
        matched = async_kivy_app.resolve_widget().down(
            lambda w: w.__class__.__name__ == cls_name)()
        assert matched is ids[cls_name.lower()].__self__

    with pytest.raises(ResolverNotFound):
        async_kivy_app.resolve_widget().down(
            lambda w: w.__class__.__name__ == 'Something')


async def test_resolve_up(async_kivy_app):
    await async_kivy_app(create_kv_app)
    ids = async_kivy_app.app.root.ids

    bottom = async_kivy_app.resolve_widget().down(name='widget')()
    matched = async_kivy_app.resolve_widget(bottom).up(name='a1')()
    assert matched is ids['a1'].__self__

    with pytest.raises(ResolverNotFound):
        async_kivy_app.resolve_widget(bottom).up(name='a11')

    bottom = async_kivy_app.resolve_widget().down(name='a21')()
    matched = async_kivy_app.resolve_widget(bottom).up(name='a2')()
    assert matched is ids['a2'].__self__

    with pytest.raises(ResolverNotFound):
        async_kivy_app.resolve_widget(bottom).up(name='hello')
    with pytest.raises(ResolverNotFound):
        async_kivy_app.resolve_widget(bottom).up(name='a1')


async def test_resolve_chain(async_kivy_app):
    await async_kivy_app(create_kv_app)
    ids = async_kivy_app.app.root.ids

    matched = async_kivy_app.resolve_widget().down(
        name='widget').up(name='a1')()
    assert matched is ids['a1'].__self__

    matched = async_kivy_app.resolve_widget().down(name='a21').up(name='a2')()
    assert matched is ids['a2'].__self__


async def test_resolve_family_up(async_kivy_app):
    await async_kivy_app(create_kv_app)
    ids = async_kivy_app.app.root.ids
    names = ['a1', 'a11', 'widget', 'a2', 'a21']

    for base_name in names:
        bottom = async_kivy_app.resolve_widget().down(name=base_name)()
        for find_name in names:
            matched = async_kivy_app.resolve_widget(bottom).family_up(
                name=find_name)()
            assert matched is ids[find_name].__self__


async def test_resolve_down_func_and_name(async_kivy_app):
    await async_kivy_app(create_kv_app)
    ids = async_kivy_app.app.root.ids

    matched = async_kivy_app.resolve_widget().down(
        lambda w: w.__class__.__name__ == 'Label', text='hello')()
    assert matched is ids['label'].__self__

    matched = async_kivy_app.resolve_widget().down(
        lambda w: w.__class__.__name__ == 'Button', text='hello')()
    assert matched is ids['button'].__self__
