if __name__ == "init":
    params.define("font", Font("monospace"))
    params.define("text", Text(default="foo"))
    params.define("multiline", Text(default="foo\nbar", multiline=True))
    params.define("fill", Color(r=1.0))
    params.define("stroke", Color())
    params.define("radius", Numeric(0, 100, 1, 10))
    params.define("line_width", Infinite(1.0))
    params.define("show_text", Toggle(True))
    params.define("angle", Angle(0))

    # Simplest case, value is the same as the item name.
    params.define(
        "shape",
        Choice(
            ["Circle", "Square", "Triangle"],
            "Triangle"))

    # More complex case, a mapping of keys to values"
    params.define(
        "antialias",
        Choice({
            "Default": cairo.Antialias.DEFAULT,
            "None": cairo.Antialias.NONE,
            "Gray": cairo.Antialias.GRAY,
            "Subpixel": cairo.Antialias.SUBPIXEL,
            "Fast": cairo.Antialias.FAST,
            "Good": cairo.Antialias.GOOD,
            "Best": cairo.Antialias.BEST
        }, "Default"))

    params.define("image", Image(cairo.SolidPattern(0, 0, 0)))
else:
    cr.set_antialias(params["antialias"])
    cr.set_font_size(24)
    (x,y) = window.center

    shape = params["shape"]
    radius = params["radius"]

    cr.set_source(params["image"])
    helpers.center_rect(Point(100, 300), 100, 100)
    cr.fill()

    # this is the official cairo API for saves and restores.
    cr.save()
    cr.translate(x, y)
    cr.rotate(params["angle"])
    if shape == "Circle":
        helpers.circle(Point(0,0), params["radius"])
    elif shape == "Square":
        helpers.center_rect(Point(0,0), radius, radius)
    elif shape == "Triangle":
        with helpers.save():
            cr.move_to(radius, 0)

        with helpers.save():
            cr.rotate(2 * math.pi / 3)
            cr.line_to(radius, 0)

        with helpers.save():
            cr.rotate(-2 * math.pi / 3)
            cr.line_to(radius, 0)

        cr.close_path()

    # heaven help you if you forget the matching restore()
    cr.restore()
    cr.set_source(params["fill"])
    cr.fill_preserve()
    cr.set_line_width(params["line_width"])
    cr.set_source(params["stroke"])
    cr.stroke()

    if params["show_text"]:
        with helpers.save():
            cr.translate(x, y)
            cr.rotate(params["angle"])
            cr.move_to(0, 0)
            helpers.center_text(params["text"], params["font"])

        cr.move_to(window.center.x, 100)
        helpers.center_text(params["multiline"], params["font"])
