if __name__ == "init":
    params.define("nodes", Numeric(4, 100, 1, 80))
    params.define("amplitude", Numeric(2, 500, 1, 43))
    params.define("frequency", Numeric(1, 30, 1, 3))
    params.define("phase_sep", Numeric(1, 512, 1, 256))
    params.define("color", Color(1, 0, 0, 0.75))
    params.define("line_width", Numeric(1.0, 50.0, 0.5, 3))
else:
    nodes = int(params["nodes"])
    amplitude = params["amplitude"]
    phase_sep = 2 * math.pi / params["phase_sep"]
    frequency = params["frequency"]

    with helpers.box(window.inset(10), clip=True) as layout:
        spacing = layout.width / nodes
        start = layout.west().x

        cr.set_source(params["color"])
        cr.set_line_width(params["line_width"])

        point = Point(layout.west().x, 0)
        helpers.move_to(layout.west())
        for i in range(1, nodes - 1):
            helpers.line_to(Point(
                start + i * spacing,
                amplitude * math.sin(time * frequency + i * phase_sep)))

        helpers.line_to(layout.east())
        cr.stroke()

        cr.set_source_rgb(0, 0, 0)
        helpers.rect(layout)
        cr.set_line_width(10.0)
        cr.stroke()

