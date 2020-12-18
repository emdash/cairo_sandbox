if __name__ == "init":
    import math
    params.define("from_stdin", Toggle(False))
    params.define("arc_length", Angle(4.897, ))
    params.define("min_rpm", Numeric(0, 20000, 1, 0))
    params.define("max_rpm", Numeric(0, 20000, 1, 6500))
    params.define("redline", Numeric(0, 20000, 1, 6000))
    params.define("ticks", Numeric(1, 5000, 1, 500))
    params.define("hub_radius", Numeric(2, 100, 1, 20))
    params.define("number_radius", Numeric(0, 1, 1/256.0, 0.8))
    params.define("tick_radius", Numeric(0, 1, 1/256.0, 0.475))
    params.define("needle_radius", Numeric(0, 1, 1/256.0, 0.6))
    params.define("tick_length", Numeric(0, 1, 1/256.0, 0.150))
    params.define("rpm", Numeric(0, 6500, 1, 1000))
    params.define("show_outline", Toggle(False))
    params.define("radial_numbers", Toggle(False))
    params.define("background_color", Color(0, 0, 0))
    params.define("dial_color", Color(0xED/255, 0xD4/255, 0))
    params.define("needle_color", Color(1, 0, 0))
    params.define("text_size", Numeric(0, 52, 1, 11))
    params.define("label", Text("RPM x 100"))
    params.define("label_offset", Infinite(-20))
    params.setResolution(1600, 900)
else:
    arc_length = params["arc_length"]
    arc_remainder = 2 * math.pi - arc_length
    min_rpm = params["min_rpm"]
    max_rpm = params["max_rpm"]
    redline = params["redline"]
    ticks = params["ticks"]
    start = arc_remainder / 2 + math.pi / 2
    end = start + arc_length

    def rpm_to_angle(rpm):
        rpm_range = max_rpm - min_rpm
        percent = rpm / rpm_range
        return percent * arc_length + start

    cr.set_source(params["background_color"])
    cr.paint()
    cr.set_source(params["dial_color"])

    with helpers.box(window.inset(5), clip=False) as bounds:
        radius = min(bounds.width, bounds.height) * 0.5
        hub_radius = max(5, radius / params["hub_radius"])

        cr.set_line_width(4.0)
        cr.set_line_cap(cairo.LineCap.ROUND)
        cr.set_font_size(params["text_size"])
        for tick in range(int(min_rpm), int(max_rpm), int(ticks)):
            with helpers.save():
                angle = rpm_to_angle(tick)
                cr.rotate(angle)
                cr.move_to(radius * params["tick_radius"], 0)
                cr.line_to(radius * params["tick_radius"] + radius * params["tick_length"], 0)
                cr.translate(radius * params["number_radius"], 0)
                if params["radial_numbers"]:
                    cr.rotate(math.pi / 2)
                else:
                    cr.rotate(-angle)
                cr.move_to(0, 0)
                helpers.center_text(str("%d" % (tick / 100)))

        cr.stroke()

        cr.set_font_size(5)
        helpers.move_to(bounds.center + Point(0, params["label_offset"]))
        helpers.center_text(params["label"])

        if params["show_outline"]:
            cr.translate(*bounds.center)
            cr.arc(0, 0, radius, start, end)
            cr.close_path()
            cr.stroke()

        cr.set_source(params["needle_color"])

        with helpers.save():
            if params["from_stdin"]:
                cr.rotate(rpm_to_angle(stdin["rpm"]))
            else:
                cr.rotate(rpm_to_angle(params["rpm"]))
            cr.move_to(radius * params["needle_radius"], 0)
            cr.line_to(0, hub_radius)
            cr.line_to(0, -hub_radius)
            cr.close_path()
            cr.fill()

        helpers.circle(Point(0, 0), hub_radius)
        cr.fill()
        
