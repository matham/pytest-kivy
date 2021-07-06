"""App
======

The wrapper app to help test Kivy apps.

"""

import random
import sys
import time
import math
import os

from pytest_kivy.resolver import WidgetResolver

__all__ = ('AsyncUnitApp', )


class AsyncUnitApp:
    """Wrapper app that provides methods to test parts of a Kivy App
    asynchronously.
    """

    app_has_started = False

    app_has_stopped = False

    app = None

    _context = None

    _nursery = None

    _event_loop = None

    _start_exception = None

    _async_start_task = None

    width = 320

    height = 240

    async_lib = os.environ.get('KIVY_EVENTLOOP', 'asyncio')

    def __init__(
            self, nursery=None, event_loop=None, width=320, height=240,
            async_lib=os.environ.get('KIVY_EVENTLOOP', 'asyncio')):
        super().__init__()
        self._nursery = nursery
        self._event_loop = event_loop
        self.width = width
        self.height = height
        self.async_lib = async_lib

    def set_kivy_config(self):
        from kivy.config import Config
        Config.set('graphics', 'width', str(self.width))
        Config.set('graphics', 'height', str(self.height))
        for items in Config.items('input'):
            Config.remove_option('input', items[0])

    async def __aenter__(self):
        self.set_kivy_config()

        from kivy.core.window import Window
        from kivy.context import Context
        from kivy.clock import ClockBase
        from kivy.factory import FactoryBase, Factory
        from kivy.lang.builder import BuilderBase, Builder

        kivy_eventloop = self.async_lib
        if kivy_eventloop == 'asyncio':
            try:
                import pytest_asyncio
            except ImportError as e:
                raise TypeError(
                    'KIVY_EVENTLOOP is asyncio but "pytest_asyncio" is not '
                    'installed') from e
            async_lib = 'asyncio'
        elif kivy_eventloop == 'trio':
            try:
                import pytest_trio
            except ImportError as e:
                raise TypeError(
                    'KIVY_EVENTLOOP is trio but "pytest_trio" is not '
                    'installed') from e
            async_lib = 'trio'
        else:
            raise TypeError(f'unknown event loop {kivy_eventloop}')

        self._context = context = Context(init=False)
        context['Clock'] = ClockBase(async_lib=async_lib)
        # have to make sure all global kv files are loaded before this because
        # globally read kv files (e.g. on module import) will not be loaded
        # again in the new builder, except if manually loaded, which we don't
        # context['Factory'] = FactoryBase.create_from(Factory)
        # context['Builder'] = BuilderBase.create_from(Builder)
        context.push()

        Window.create_window()
        Window.register()
        Window.initialized = True
        Window.canvas.clear()
        Window.size = self.width, self.height

        from kivy.clock import Clock
        Clock._max_fps = 0
        Clock.init_async_lib(async_lib)
        return self

    async def __call__(self, app_cls):
        self.app = app = app_cls()

        def started_app(*largs):
            self.app_has_started = True
        app.fbind('on_start', started_app)

        def stopped_app(*largs):
            self.app_has_stopped = True
        app.fbind('on_stop', stopped_app)

        if self.async_lib == 'asyncio':
            # task must be canceled if exception is raised before started
            self._async_start_task = self._event_loop.create_task(
                self._run_app())
        else:
            self._nursery.start_soon(self._run_app)

        try:
            # if _run_app raises, trio seems to get stuck, so don't wait forever
            ts = time.perf_counter()
            while not self.app_has_started and self._start_exception is None:
                await self.async_sleep(.1)
                if time.perf_counter() - ts >= 120:
                    raise TimeoutError()

            from kivy.clock import Clock
            frames_end = Clock.frames + 5
            while Clock.frames < frames_end and self._start_exception is None:
                await self.async_sleep(1 / 60.)

            return app
        finally:
            self.raise_startup_exception()

    async def wait_stop_app(self):
        if self.app is None:
            return

        from kivy.base import stopTouchApp, EventLoop
        stopTouchApp()
        await self.async_sleep(0)
        if EventLoop.status == 'idle':
            # it never started so don't wait to start
            return

        ts = time.perf_counter()
        while not self.app_has_stopped:
            await self.async_sleep(.1)
            if time.perf_counter() - ts >= 60:
                raise TimeoutError()

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        from kivy.core.window import Window
        from kivy.animation import Animation
        from kivy.base import stopTouchApp
        from kivy.logger import LoggerHistory

        stopTouchApp()
        for anim in list(Animation._instances):
            anim._unregister()
        for child in Window.children[:]:
            Window.remove_widget(child)

        self._context.pop()
        self._context = None
        LoggerHistory.clear_history()

    async def _run_app(self):
        try:
            await self.app.async_run()
        except BaseException:
            self._start_exception = sys.exc_info()
            raise

    def raise_startup_exception(self):
        """(internal) Trio seems to get stuck if app startup fails. So we
        check startup status in the fixture before yielding app.
        """
        if self.async_lib == 'asyncio' and self._start_exception is not None:
            tp, value, tb = self._start_exception
            self._start_exception = None
            if self._async_start_task is not None:
                self._async_start_task.cancel()
                self._async_start_task = None
            raise value.with_traceback(tb)

    async def async_sleep(self, delay):
        from kivy.clock import Clock
        await Clock._async_lib.sleep(delay)

    def resolve_widget(self, base_widget=None):
        if base_widget is None:
            from kivy.core.window import Window
            base_widget = Window
        return WidgetResolver(base_widget=base_widget)

    async def wait_clock_frames(
            self, n: int, sleep_time: float = 1 / 60.) -> int:
        from kivy.clock import Clock
        frames_start = Clock.frames
        while Clock.frames < frames_start + n:
            await self.async_sleep(sleep_time)
        return Clock.frames

    def get_widget_pos_pixel(self, widget, positions):
        from kivy.graphics import Fbo, ClearColor, ClearBuffers

        canvas_parent_index = -2
        if widget.parent is not None:
            canvas_parent_index = widget.parent.canvas.indexof(widget.canvas)
            if canvas_parent_index > -1:
                widget.parent.canvas.remove(widget.canvas)

        w, h = int(widget.width), int(widget.height)
        fbo = Fbo(size=(w, h), with_stencilbuffer=True)

        with fbo:
            ClearColor(0, 0, 0, 0)
            ClearBuffers()

        fbo.add(widget.canvas)
        fbo.draw()
        pixels = fbo.pixels
        fbo.remove(widget.canvas)

        if widget.parent is not None and canvas_parent_index > -1:
            widget.parent.canvas.insert(canvas_parent_index, widget.canvas)

        values = []
        for x, y in positions:
            x = int(x)
            y = int(y)
            i = y * w * 4 + x * 4
            values.append(tuple(pixels[i:i + 4]))

        return values

    async def do_touch_down_up(
            self, pos=None, widget=None, duration=.2, pos_jitter=None,
            widget_jitter=False, jitter_dt=1 / 15., end_on_pos=False):
        from pytest_kivy.input import AsyncUnitTestTouch
        if widget is None:
            x, y = pos
        else:
            if pos is None:
                x, y = widget.to_window(*widget.center)
            else:
                x, y = widget.to_window(*pos, initial=False)
        touch = AsyncUnitTestTouch(x, y)

        ts = time.perf_counter()
        touch.touch_down()
        await self.wait_clock_frames(1)
        yield 'down', touch.pos

        if not pos_jitter and not widget_jitter:
            await self.async_sleep(duration)
            touch.touch_up()
            await self.wait_clock_frames(1)
            yield 'up', touch.pos

            return

        moved = False
        if pos_jitter:
            dx, dy = pos_jitter
        else:
            dx = widget.width / 2.
            dy = widget.height / 2.

        while time.perf_counter() - ts < duration:
            moved = True
            await self.async_sleep(jitter_dt)

            touch.touch_move(
                x + (random.random() * 2 - 1) * dx,
                y + (random.random() * 2 - 1) * dy
            )
            await self.wait_clock_frames(1)
            yield 'move', touch.pos

        if end_on_pos and moved:
            touch.touch_move(x, y)
            await self.wait_clock_frames(1)
            yield 'move', touch.pos

        touch.touch_up()
        await self.wait_clock_frames(1)
        yield 'up', touch.pos

    async def do_touch_drag(
            self, pos=None, widget=None,
            widget_loc=('center_x', 'center_y'), dx=0, dy=0,
            target_pos=None, target_widget=None, target_widget_offset=(0, 0),
            target_widget_loc=('center_x', 'center_y'), long_press=0,
            duration=.2, drag_n=5):
        """Initiates a touch down, followed by some dragging to a target
        location, ending with a touch up.

        `origin`: These parameters specify where the drag starts.

        - If ``widget`` is None, it starts at ``pos`` (in window coordinates).
          If ``dx``/``dy`` is used, it is in the window coordinate system also.
        - If ``pos`` is None, it starts on the ``widget`` as specified by
          ``widget_loc``. If ``dx``/``dy`` is used, it is in the ``widget``
          coordinate system.
        - If neither is None, it starts at ``pos``, but in the ``widget``'s
          coordinate system (:meth:`~kivy.uix.widget.Widget.to_window` is used
          on it). If ``dx``/``dy`` is used, it is in the ``widget``
          coordinate system.

        `target`: These parameters specify where the drag ends.

        - If ``target_pos`` and ``target_widget`` is None, then ``dx`` and
          ``dy`` is used relative to the position where the drag started.
        - If ``target_widget`` is None, it ends at ``target_pos``
          (in window coordinates).
        - If ``target_pos`` is None, it ends on the ``target_widget`` as
          specified by ``target_widget_loc``. ``target_widget_offset``, is an
          additional ``(x, y)`` offset relative to ``target_widget_loc``.
        - If neither is None, it starts at ``target_pos``, but in the
          ``target_widget``'s coordinate system
          (:meth:`~kivy.uix.widget.Widget.to_window` is used on it).

        When ``widget`` and/or ``target_widget`` are specified, ``widget_loc``
        and ``target_widget_loc``, respectively, indicate where on the widget
        the drag starts/ends. It is a a tuple with property names of the widget
        to loop up to get the value. The default is
        ``('center_x', 'center_y')`` so the drag would start/end in the
        widget's center.
        """
        from pytest_kivy.input import AsyncUnitTestTouch
        if widget is None:
            x, y = pos
            tx, ty = x + dx, y + dy
        else:
            if pos is None:
                w_x = getattr(widget, widget_loc[0])
                w_y = getattr(widget, widget_loc[1])
                x, y = widget.to_window(w_x, w_y)
                tx, ty = widget.to_window(w_x + dx, w_y + dy)
            else:
                x, y = widget.to_window(*pos, initial=False)
                tx, ty = widget.to_window(
                    pos[0] + dx, pos[1] + dy, initial=False)

        if target_pos is not None:
            if target_widget is None:
                tx, ty = target_pos
            else:
                tx, ty = target_pos = target_widget.to_window(
                    *target_pos, initial=False)
        elif target_widget is not None:
            x_off, y_off = target_widget_offset
            w_x = getattr(target_widget, target_widget_loc[0]) + x_off
            w_y = getattr(target_widget, target_widget_loc[1]) + y_off
            tx, ty = target_pos = target_widget.to_window(w_x, w_y)
        else:
            target_pos = tx, ty

        touch = AsyncUnitTestTouch(x, y)

        touch.touch_down()
        await self.wait_clock_frames(1)
        if long_press:
            await self.async_sleep(long_press)
        yield 'down', touch.pos

        dx = (tx - x) / drag_n
        dy = (ty - y) / drag_n

        ts0 = time.perf_counter()
        for i in range(drag_n):
            await self.async_sleep(
                max(0., duration - (time.perf_counter() - ts0)) / (drag_n - i))

            touch.touch_move(x + (i + 1) * dx, y + (i + 1) * dy)
            await self.wait_clock_frames(1)
            yield 'move', touch.pos

        if touch.pos != target_pos:
            touch.touch_move(*target_pos)
            await self.wait_clock_frames(1)
            yield 'move', touch.pos

        touch.touch_up()
        await self.wait_clock_frames(1)
        yield 'up', touch.pos

    async def do_touch_drag_follow(
            self, pos=None, widget=None,
            widget_loc=('center_x', 'center_y'),
            target_pos=None, target_widget=None, target_widget_offset=(0, 0),
            target_widget_loc=('center_x', 'center_y'), long_press=0,
            duration=.2, drag_n=5, max_n=25, abs_tol=1):
        """Very similar to :meth:`do_touch_drag`, except it follows the target
        widget, even if the target widget moves as a result of the drag, the
        drag will follow it until it's on the target widget.

        `origin`: These parameters specify where the drag starts.

        - If ``widget`` is None, it starts at ``pos`` (in window coordinates).
        - If ``pos`` is None, it starts on the ``widget`` as specified by
          ``widget_loc``.
        - If neither is None, it starts at ``pos``, but in the ``widget``'s
          coordinate system (:meth:`~kivy.uix.widget.Widget.to_window` is used
          on it).

        `target`: These parameters specify where the drag ends.

        - If ``target_pos`` is None, it ends on the ``target_widget`` as
          specified by ``target_widget_loc``. ``target_widget_offset``, is an
          additional ``(x, y)`` offset relative to ``target_widget_loc``.
        - If ``target_pos`` is not None, it starts at ``target_pos``, but in
          the ``target_widget``'s coordinate system
          (:meth:`~kivy.uix.widget.Widget.to_window` is used on it).

        When ``widget`` and/or ``target_widget`` are specified, ``widget_loc``
        and ``target_widget_loc``, respectively, indicate where on the widget
        the drag starts/ends. It is a a tuple with property names of the widget
        to loop up to get the value. The default is
        ``('center_x', 'center_y')`` so the drag would start/end in the
        widget's center.
        """
        from pytest_kivy.input import AsyncUnitTestTouch
        if widget is None:
            x, y = pos
        else:
            if pos is None:
                w_x = getattr(widget, widget_loc[0])
                w_y = getattr(widget, widget_loc[1])
                x, y = widget.to_window(w_x, w_y)
            else:
                x, y = widget.to_window(*pos, initial=False)

        if target_widget is None:
            raise ValueError('target_widget must be specified')

        def get_target():
            if target_pos is not None:
                return target_widget.to_window(*target_pos, initial=False)
            else:
                x_off, y_off = target_widget_offset
                wt_x = getattr(target_widget, target_widget_loc[0]) + x_off
                wt_y = getattr(target_widget, target_widget_loc[1]) + y_off
                return target_widget.to_window(wt_x, wt_y)

        touch = AsyncUnitTestTouch(x, y)

        touch.touch_down()
        await self.wait_clock_frames(1)
        if long_press:
            await self.async_sleep(long_press)
        yield 'down', touch.pos

        ts0 = time.perf_counter()
        tx, ty = get_target()
        i = 0
        while not (math.isclose(touch.x, tx, abs_tol=abs_tol) and
                   math.isclose(touch.y, ty, abs_tol=abs_tol)):
            if i >= max_n:
                raise Exception(
                    'Exceeded the maximum number of iterations, '
                    'but {} != {}'.format(touch.pos, (tx, ty)))

            rem_i = max(1, drag_n - i)
            rem_t = max(0., duration - (time.perf_counter() - ts0)) / rem_i
            i += 1
            await self.async_sleep(rem_t)

            x, y = touch.pos
            touch.touch_move(x + (tx - x) / rem_i, y + (ty - y) / rem_i)
            await self.wait_clock_frames(1)
            yield 'move', touch.pos
            tx, ty = get_target()

        touch.touch_up()
        await self.wait_clock_frames(1)
        yield 'up', touch.pos

    async def do_touch_drag_path(
            self, path, axis_widget=None, long_press=0, duration=.2):
        """Drags the touch along the specified path.

        :parameters:

            `path`: list
                A list of position tuples the touch will follow. The first
                item is used for the touch down and the rest for the move.
            `axis_widget`: a Widget
                If None, the path coordinates is in window coordinates,
                otherwise, we will first transform the path coordinates
                to window coordinates using
                :meth:`~kivy.uix.widget.Widget.to_window` of the specified
                widget.
        """
        from pytest_kivy.input import AsyncUnitTestTouch
        if axis_widget is not None:
            path = [axis_widget.to_window(*p, initial=False) for p in path]
        x, y = path[0]
        path = path[1:]

        touch = AsyncUnitTestTouch(x, y)

        touch.touch_down()
        await self.wait_clock_frames(1)
        if long_press:
            await self.async_sleep(long_press)
        yield 'down', touch.pos

        ts0 = time.perf_counter()
        n = len(path)
        for i, (x2, y2) in enumerate(path):
            await self.async_sleep(
                max(0., duration - (time.perf_counter() - ts0)) / (n - i))

            touch.touch_move(x2, y2)
            await self.wait_clock_frames(1)
            yield 'move', touch.pos

        touch.touch_up()
        await self.wait_clock_frames(1)
        yield 'up', touch.pos

    async def do_keyboard_key(
            self, key, modifiers=(), duration=.05, num_press=1):
        from kivy.core.window import Window
        if key == ' ':
            key = 'spacebar'
        key_lower = key.lower()
        key_code = Window._system_keyboard.string_to_keycode(key_lower)

        known_modifiers = {'shift', 'alt', 'ctrl', 'meta'}
        if set(modifiers) - known_modifiers:
            raise ValueError('Unknown modifiers "{}"'.
                             format(set(modifiers) - known_modifiers))

        special_keys = {
            27: 'escape',
            9: 'tab',
            8: 'backspace',
            13: 'enter',
            127: 'del',
            271: 'enter',
            273: 'up',
            274: 'down',
            275: 'right',
            276: 'left',
            278: 'home',
            279: 'end',
            280: 'pgup',
            281: 'pgdown',
            300: 'numlock',
            301: 'capslock',
            145: 'screenlock',
        }

        text = None
        try:
            text = chr(key_code)
            if key_lower != key:
                text = key
        except ValueError:
            pass

        dt = duration / num_press
        for i in range(num_press):
            await self.async_sleep(dt)

            Window.dispatch('on_key_down', key_code, 0, text, modifiers)
            if (key not in known_modifiers and
                    key_code not in special_keys and
                    not (known_modifiers & set(modifiers))):
                Window.dispatch('on_textinput', text)

            await self.wait_clock_frames(1)
            yield 'down', (key, key_code, 0, text, modifiers)

        Window.dispatch('on_key_up', key_code, 0)
        await self.wait_clock_frames(1)
        yield 'up', (key, key_code, 0, text, modifiers)
