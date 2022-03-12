"""Demonstrates the use of the `grid` method on Rect objects.
"""

if __name__ == "init":
    params.define("rows",        Numeric(1, 100, 1, 5))
    params.define("cols",        Numeric(1, 100, 1, 5))
    params.define("row",         Numeric(1, 100, 1, 1))
    params.define("col",         Numeric(1, 100, 1, 1))
    params.define("font",        Font("monospace 3"))
    params.define("col_first",   Toggle(True))
    params.define("show_guides", Toggle(False))
else:
    g = window.grid(int(cols), int(rows))
    cr.set_source_rgb(1, 1, 1)
    cr.paint()

    cr.set_source_rgb(0, 0, 0)
    for (i, cell) in enumerate(g.cells(col_first)):
        with helpers.box(cell):
            cr.move_to(0, 0)
            helpers.center_text(str(i), font)

    with helpers.box(g.cell(int(col), int(row))) as cell:
        cr.set_source_rgb(1, 0, 0)
        helpers.circle(Point(0, 0), cell.radius() - 5)
        cr.stroke()

    if show_guides:
        g.debug(helpers)
