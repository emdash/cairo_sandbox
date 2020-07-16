if __name__ == "init":
    params.define("text", Text(default="foo"))
    params.define("multiline", Text(default="foo\nbar", multiline=True))
    params.define("fill", Color(r=1.0))
    params.define("stroke", Color())
    params.define("radius", Numeric(0, 100, 1, 10))
    params.define("line_width", Numeric(0, 20, 1, 2))
else:
    (x,y) = window.center
    cr.arc(x, y, params["radius"], 0, math.pi * 2)
    cr.set_source(params["fill"])
    cr.fill_preserve()
    cr.set_line_width(params["line_width"])
    cr.set_source(params["stroke"])
    cr.stroke()

    cr.move_to(*window.center)
    cr.show_text(params["text"])

    cr.move_to(window.center.x, 100)
    cr.show_text(params["multiline"])
