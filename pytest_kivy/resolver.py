"""Resolver
===========

Resolves individual widgets, given a root widget to help locate and test
a specific widget in the widget tree.

"""

from collections import deque

__all__ = ('WidgetResolver', 'ResolverNotFound')

_unique_value = object


class ResolverNotFound(ValueError):
    pass


class WidgetResolver:
    """It assumes that the widget tree strictly forms a DAG.
    """

    base_widget = None

    matched_widget = None

    _kwargs_filter = {}

    _funcs_filter = []

    def __init__(self, base_widget, **kwargs):
        self.base_widget = base_widget
        self._kwargs_filter = {}
        self._funcs_filter = []
        super(WidgetResolver, self).__init__(**kwargs)

    def __call__(self):
        if self.matched_widget is not None:
            return self.matched_widget

        if not self._kwargs_filter and not self._funcs_filter:
            return self.base_widget
        return None

    def match(self, **kwargs_filter):
        self._kwargs_filter.update(kwargs_filter)
        return self

    def match_funcs(self, funcs_filter=()):
        self._funcs_filter.extend(funcs_filter)
        return self

    def check_widget(self, widget):
        if not all(func(widget) for func in self._funcs_filter):
            return False

        for attr, val in self._kwargs_filter.items():
            if getattr(widget, attr, _unique_value) != val:
                return False

        return True

    def not_found(self, op):
        raise ResolverNotFound(
            'Cannot find widget matching <{}, {}> starting from base '
            'widget "{}" doing "{}" traversal'.format(
                self._kwargs_filter, self._funcs_filter, self.base_widget, op))

    def down(self, *__funcs_filter, **kwargs_filter):
        self.match(**kwargs_filter)
        self.match_funcs(__funcs_filter)
        check = self.check_widget

        fifo = deque([self.base_widget])
        while fifo:
            widget = fifo.popleft()
            if check(widget):
                return WidgetResolver(base_widget=widget)

            fifo.extend(widget.children)

        self.not_found('down')

    def up(self, *__funcs_filter, **kwargs_filter):
        self.match(**kwargs_filter)
        self.match_funcs(__funcs_filter)
        check = self.check_widget

        parent = self.base_widget
        while parent is not None:
            if check(parent):
                return WidgetResolver(base_widget=parent)

            new_parent = parent.parent
            # Window is its own parent oO
            if new_parent is parent:
                break
            parent = new_parent

        self.not_found('up')

    def family_up(self, *__funcs_filter, **kwargs_filter):
        self.match(**kwargs_filter)
        self.match_funcs(__funcs_filter)
        check = self.check_widget

        base_widget = self.base_widget
        already_checked_base = None
        while base_widget is not None:
            fifo = deque([base_widget])
            while fifo:
                widget = fifo.popleft()
                # don't check the child we checked before moving up
                if widget is already_checked_base:
                    continue

                if check(widget):
                    return WidgetResolver(base_widget=widget)

                fifo.extend(widget.children)

            already_checked_base = base_widget
            new_base_widget = base_widget.parent
            # Window is its own parent oO
            if new_base_widget is base_widget:
                break
            base_widget = new_base_widget

        self.not_found('family_up')
