if __name__ == "init":
    params.define("test", Text(default="foo"))
    params.define("fill", Color(r=1.0))
    params.define("stroke", Color())
    params.define("radius", Numeric(0, 50, 1, 5))
    params.define("line_width", Numeric(0, 10, 1, 0))
else:
    (x,y) = window.center
    cr.arc(x, y, params["radius"], 0, math.pi * 2)
    cr.set_source(params["fill"])
    cr.fill_preserve()
    cr.set_line_width(params["line_width"])
    cr.set_source(params["stroke"])
    cr.stroke()

    cr.move_to(*window.center)
    cr.show_text(params["test"])
