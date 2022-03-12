"""Demonstrates the use of the `guides` method on Rect objects.

Creates a simple 3-pane layout, common among web pages. In some ways this is a
bad example, since you should probably use split_left in order to specify an
absolute width for the side bar, rather than a percentage width.

But let's not worry about that for now.
"""

if __name__ == "init":
    params.define("side_bar",    Numeric(0, 1, 1/128, 1/3))
    params.define("status_bar",  Numeric(0, 1, 1/128, 15/16))
    params.define("background",  Color(1, 1, 1))
    params.define("text",        Color())
    params.define("font",        Font("monospace 3"))
    params.define("show_guides", Toggle(False))
else:
    g = window.guides((side_bar,), (status_bar,))

    helpers.rect(window)
    cr.set_source(background)
    cr.fill()

    cr.set_source(text)
    with helpers.box(g.cell(0, 0)):
        cr.move_to(0, 0)
        helpers.center_text("Sidebar", font)

    with helpers.box(g.cell(1, 0)) as content:
        helpers.circle(Point(0, 0), content.radius() - 5)
        with helpers.save():
            cr.set_source_rgba(1, 0, 0, 0.5)
            cr.fill()
        cr.move_to(0, 0)
        helpers.center_text("Content Region", font)

    with helpers.box(g.row(1)) as status:
        cr.move_to(0, 0)
        cr.set_source(text)
        helpers.center_text("Status Bar", font)

    if show_guides:
        g.debug(helpers)
    else:
        cr.set_line_width(2)
        cr.set_source_rgba(0, 0, 0, 0.5)
        helpers.hline(g.horizontal[1], window)
        helpers.move_to(g.intersection(1, 0))
        helpers.line_to(g.intersection(1, 1))
        cr.stroke()
