"""Input
========

Input classes that can be used to simulate deice (e.g. mouse) input.
"""
from kivy.tests import UnitTestTouch

__all__ = ('AsyncUnitTestTouch', )


class AsyncUnitTestTouch(UnitTestTouch):

    def __init__(self, *largs, **kwargs):
        self.grab_exclusive_class = None
        self.is_touch = True
        super(AsyncUnitTestTouch, self).__init__(*largs, **kwargs)

    def touch_down(self, *args):
        self.eventloop._dispatch_input("begin", self)

    def touch_move(self, x, y):
        win = self.eventloop.window
        self.move({
            "x": x / (win.width - 1.0),
            "y": y / (win.height - 1.0)
        })
        self.eventloop._dispatch_input("update", self)

    def touch_up(self, *args):
        self.eventloop._dispatch_input("end", self)
