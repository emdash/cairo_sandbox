#!/usr/bin/python3
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

import traceback

import cairo
import helpers
import sys


class Script(object):

    """Loads and runs the script given at `path`."""

    def __init__(self, path, reader, render_tb=True, halt_on_exc=False):
        self.transform = None
        self.reader = reader
        self.load_error = None
        self.path = path
        self.prog = None
        self.dc = None
        self.params = None
        self.render_tb = render_tb
        self.halt_on_exc = halt_on_exc

    def reload(self, param_group):
        self.params = param_group
        self.prog = compile(open(self.path, "r").read(), self.path, "exec")

        if self.halt_on_exc:
            exec(self.prog, param_group.getInitEnv())
        else:
            try:
                exec(self.prog, param_group.getInitEnv())
            except BaseException as e:
                traceback.print_exc()
                self.load_error = e

    def run(self, cr, scale, window):
        with helpers.Save(cr):
            error = None

            # scripts are dimensioned in mm.
            cr.scale(scale.x, scale.y)
            window = helpers.Rect.from_top_left(
                helpers.Point(0, 0),
                window.width / scale.x,
                window.height / scale.y)

            # Trap all errors for the script, so we can display them
            # nicely.
            if not self.halt_on_exc:
                try:
                    exec(self.prog,
                        self.params.getRenderEnv(cr, scale, window, self.reader.env))
                except BaseException as e:
                    error = traceback.format_exc()
            else:
                exec(self.prog,
                     self.params.getRenderEnv(cr, scale, window, self.reader.env))

            self.transform = cr.get_matrix()
            self.inverse_transform = cr.get_matrix()
            self.inverse_transform.invert()

            # save the current point
            x, y = cr.get_current_point()

        with helpers.Save(cr):
            # stroke any residual path for feedback
            cr.set_operator(cairo.OPERATOR_DIFFERENCE)
            cr.set_source_rgb(1.0, 1.0, 1.0)
            cr.set_line_width(0.1)
            cr.stroke()

        with helpers.Save(cr):
            cr.set_source_rgb(1.0, 1.0, 1.0)
            cr.set_operator(cairo.OPERATOR_DIFFERENCE)
            # draw the current point.
            x, y = self.transform.transform_point(x, y)
            cr.translate(x, y)
            cr.move_to(-5, 0)
            cr.line_to(5, 0)
            cr.move_to(0, -5)
            cr.line_to(0, 5)
            cr.stroke()

        if error is not None and self.render_tb:
            with helpers.Box(cr, window.inset(10), clip=False) as layout:
                cr.set_source_rgba(1.0, 0.0, 0.0, 0.5)
                cr.move_to(*layout.northwest())
                for line in error.split('\n'):
                    cr.show_text(line)
                    cr.translate(0, 10)
                    cr.move_to(*layout.northwest())
        elif error is not None:
            print(error, file=sys.stderr)
