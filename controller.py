# cairo-sandbox: Interactive sandbox for cairo graphics.
#
# Copyright (C) 2020  Brandon Lewis
#
# This program is free software: you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public License
# as published by the Free Software Foundation, either version 3 of
# the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public
# License along with this program.  If not, see
# <https://www.gnu.org/licenses/>.


import gi
gi.require_version("Gtk", "3.0")
gi.require_foreign("cairo")
from gi.repository import GObject
from gi.repository import Gtk
from gi.repository import Gdk


from helpers import Point


class CursorState(object):
    """ABC For the Cursor State Machine"""

    def button_press(self, event):
        raise NotImplementedError()

    def button_release(self, event):
        raise NotImplementedError()

    def mouse_move(self, event):
        raise NotImplementedError()

    def dispatch(self, callbacks):
        raise NotImplementedError()


class Hover(CursorState):

    def __init__(self, pos):
        self.pos = pos

    def button_press(self, event):
        return DragBegin(Point(event.x, event.y), self.pos)

    def button_release(self, event):
        return Hover(Point(event.x, event.y))

    def mouse_move(self, event):
        return Hover(Point(event.x, event.y))

    def dispatch(self, callbacks):
        return callbacks.hover(self)


class Click(Hover):

    def dispatch(self, callbacks):
        return callbacks.click(self)


class DragBegin(CursorState):

    def __init__(self, pos, origin):
        self.pos = pos
        self.origin = origin
        self.rel = self.pos - self.origin

    def button_press(self, event):
        return Hover(Point(event.x, event.y))

    def button_release(self, event):
        return Click(Point(event.x, event.y))

    def mouse_move(self, event):
        return DragMove(Point(event.x, event.y), self.origin)

    def dispatch(self, callbacks):
        return callbacks.begin(self)


class DragEnd(CursorState):

    drag_threshold = 1.0

    def __init__(self, pos, origin):
        self.pos = pos
        self.origin = origin
        self.rel = self.pos - self.origin

    def button_press(self, event):
        return Hover(Point(event.x, event.y))

    def button_release(self, event):
        if rel.dist() > self.drag_threshold:
            return DragEnd(Point(event.x, event.y), self.origin)
        else:
            return Click(Point(event.x, event.y))

    def mouse_move(self, event):
        return Hover(Point(event.x, event.y))

    def dispatch(self, callbacks):
        return callbacks.drop(self)


class DragMove(CursorState):

    def __init__(self, pos, origin):
        self.pos = pos
        self.origin = origin
        self.rel = self.pos - self.origin

    def button_press(self, event):
        return Hover(Point(event.x, event.y))

    def button_release(self, event):
        return DragEnd(Point(event.x, event.y), self.origin)

    def mouse_move(self, event):
        return DragMove(Point(event.x, event.y), self.origin)

    def dispatch(self, callbacks):
        return callbacks.drag(self)


class DragController(object):

    """Factor out common drag-and-drop state machine pattern.

    This interface is simpler than the platform drag-and-drop
    interface, while losing little of its power.

    The key concept we add is the `rel` parameter to the currsor state
    object. Correctly calculating `rel` parameter requires capturing
    some state at mouse-down which is preserved through the drag
    interaction.

    `callbacks` is an object which provides the following methods:
    - hover
    - begin
    - drag
    - drop

    """

    def __init__(self, widget, callbacks):
        """Creates a DragController bound to `widget.`
        """
        self.callbacks = callbacks
        self.cursor = Hover(Point(0, 0))
        widget.set_events(Gdk.EventMask.EXPOSURE_MASK
		          | Gdk.EventMask.LEAVE_NOTIFY_MASK
		          | Gdk.EventMask.BUTTON_PRESS_MASK
		          | Gdk.EventMask.BUTTON_RELEASE_MASK
		          | Gdk.EventMask.POINTER_MOTION_MASK
		          | Gdk.EventMask.POINTER_MOTION_HINT_MASK)
        widget.connect('button-press-event', self.button_press)
        widget.connect('button-release-event', self.button_release)
        widget.connect('motion-notify-event', self.mouse_move)

    def button_press(self, widget, event):
        self.cursor = self.cursor.button_press(event)
        if self.cursor.dispatch(self.callbacks):
            widget.queue_draw()

    def button_release(self, widget, event):
        self.cursor = self.cursor.button_release(event)
        if self.cursor.dispatch(self.callbacks):
            widget.queue_draw()

    def mouse_move(self, widget, event):
        self.cursor = self.cursor.mouse_move(event)
        if self.cursor.dispatch(self.callbacks):
            widget.queue_draw()


# XXX: better name for this.
class ValueController(object):

    """A special-case of DragController which binds a single value.

    Users should supply a pair of callbacks:

    - begin(cursor): the drag is beginning, cached any state if necessary.
    - updateValue(cursor): update the value based on current cursor state.
    """

    def __init__(self, widget, callbacks):
        self.dc = DragController(widget, self)
        self.callbacks = callbacks
        self.begin = callbacks.begin

    def hover(self, cursor):
        pass

    def drag(self, cursor):
        self.callbacks.updateValue(cursor)
        return True

    def drop(self, cursor):
        self.callbacks.updateValue(cursor)
        return True

    def click(self, click):
        return True
