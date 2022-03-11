if __name__ == "init":
    import math
    params.define("arc_length", Angle(4.897, ))
    params.define("min_rpm", Numeric(0, 20000, 1, 0))
    params.define("max_rpm", Numeric(0, 20000, 1, 6500))
    params.define("ticks", Numeric(1, 5000, 1, 500))
    params.define("hub_radius", Numeric(2, 100, 1, 5))
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
    params.define("label", Text("RPM x 100"))
    params.define("label_offset", Infinite(-20))
    params.define("number_font", Font("monospace bold 7"))
    params.define("label_font", Font("monospace bold 4"))
else:
    arc_remainder = 2 * math.pi - arc_length
    start = arc_remainder / 2 + math.pi / 2
    end = start + arc_length

    def rpm_to_angle(rpm):
        rpm_range = max_rpm - min_rpm
        percent = rpm / rpm_range
        return percent * arc_length + start

    cr.set_source(background_color)
    cr.paint()
    cr.set_source(dial_color)

    with helpers.box(window.inset(5), clip=False) as bounds:
        radius = min(bounds.width, bounds.height) * 0.5

        cr.set_line_width(4.0)
        cr.set_line_cap(cairo.LineCap.ROUND)
        for tick in range(int(min_rpm), int(max_rpm + ticks), int(ticks)):
            with helpers.save():
                angle = rpm_to_angle(tick)
                cr.rotate(angle)
                cr.move_to(radius * tick_radius, 0)
                cr.line_to(radius * tick_radius + radius * tick_length, 0)
                cr.translate(radius * number_radius, 0)
                if radial_numbers:
                    cr.rotate(math.pi / 2)
                else:
                    cr.rotate(-angle)
                cr.move_to(0, 0)
                helpers.center_text(str("%d" % (tick / 100)), number_font)

        cr.stroke()

        cr.set_font_size(5)
        helpers.move_to(bounds.center + Point(0, label_offset))
        helpers.center_text(label, label_font)

        if show_outline:
            cr.new_sub_path()
            cr.translate(*bounds.center)
            cr.arc(0, 0, radius, start, end)
            cr.close_path()
            cr.stroke()

        cr.set_source(needle_color)

        with helpers.save():
            cr.rotate(rpm_to_angle(rpm))
            cr.move_to(radius * needle_radius, 0)
            cr.line_to(0, hub_radius)
            cr.line_to(0, -hub_radius)
            cr.close_path()
            cr.fill()

        helpers.circle(Point(0, 0), hub_radius)
        cr.fill()
