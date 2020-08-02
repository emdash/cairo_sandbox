if __name__ == "init":
    import math
    params.define("arc-length", Angle(3 * math.pi / 2))
    params.define("min-rpm", Numeric(0, 20000, 1, 0))
    params.define("max-rpm", Numeric(0, 20000, 1, 6500))
    params.define("redline", Numeric(0, 20000, 1, 6000))
    params.define("ticks", Numeric(1, 5000, 1, 500))
    params.define("hub-radius", Numeric(2, 100, 1, 11))
    params.define("number-radius", Numeric(0, 1, 1/256.0, 0.65))
    params.define("tick-radius", Numeric(0, 1, 1/256.0, 0.80))
    params.define("needle-radius", Numeric(0, 1, 1/256.0, 0.85))
    params.define("tick-length", Numeric(0, 1, 1/256.0, 0.125))
    params.define("rpm", Numeric(0, 6500, 1, 1000))
    params.define("show-outline", Toggle(True))
    params.define("radial-numbers", Toggle(True))
    params.define("dial-color", Color(0, 0, 0))
    params.define("needle-color", Color(1, 0, 0))
else:
    arc_length = params["arc-length"]
    arc_remainder = 2 * math.pi - arc_length
    min_rpm = params["min-rpm"]
    max_rpm = params["max-rpm"]
    redline = params["redline"]
    ticks = params["ticks"]
    start = arc_remainder / 2 + math.pi / 2
    end = start + arc_length

    def rpm_to_angle(rpm):
        rpm_range = max_rpm - min_rpm
        percent = rpm / rpm_range
        return percent * arc_length + start

    cr.set_source(params["dial-color"])

    with helpers.box(window.inset(5), clip=False) as bounds:
        radius = min(bounds.width, bounds.height) * 0.5
        hub_radius = max(5, radius / params["hub-radius"])

        cr.set_line_width(5)
        cr.set_line_cap(cairo.LineCap.ROUND)
        for tick in range(int(min_rpm), int(max_rpm), int(ticks)):
            with helpers.save():
                angle = rpm_to_angle(tick)
                cr.rotate(angle)
                cr.move_to(radius * params["tick-radius"], 0)
                cr.line_to(radius * params["tick-radius"] + radius * params["tick-length"], 0)
                cr.translate(radius * params["number-radius"], 0)
                if params["radial-numbers"]:
                    cr.rotate(math.pi / 2)
                else:
                    cr.rotate(-angle)
                cr.move_to(0, 0)
                cr.set_font_size(24)
                helpers.center_text(str("%d" % (tick / 100)))

        cr.stroke()

        if params["show-outline"]:
            cr.translate(*bounds.center)
            cr.arc(0, 0, radius, start, end)
            cr.close_path()
            cr.stroke()

        cr.set_source(params["needle-color"])

        with helpers.save():
            cr.rotate(rpm_to_angle(params["rpm"]))
            cr.move_to(radius * params["needle-radius"], 0)
            cr.line_to(0, hub_radius)
            cr.line_to(0, -hub_radius)
            cr.close_path()
            cr.fill()

        helpers.circle(Point(0, 0), hub_radius)
        cr.fill()
        
