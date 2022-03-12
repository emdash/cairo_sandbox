if __name__ == "init":
    # Defines the ratio of the "narrow waist"
    params.define("text_color", Color(0))
    params.define("waist",      Text("Narrow Waist"))
    params.define("font",       Font("Nakula Bold 6"))
    params.define("tilt",       Numeric(1/128, 1, 1/128, 0.2))
else:
    def elipse(center, radius, forward, complete=False):
        with helpers.save():
            cr.new_sub_path()
            cr.translate(*center)
            cr.scale(1, tilt)

            if forward:
                start = 0
            else:
                start = math.pi

            if complete:
                end = start + 2 * math.pi
            else:
                end = start + math.pi

            if forward:
                cr.arc(0, 0, radius, start, end)
            else:
                cr.arc_negative(0, 0, radius, math.pi, 2 * math.pi)

    def hourglass(box, fill):
        with helpers.box(box, clip=False) as box:
            p = cairo.LinearGradient(*box.west(), *box.east())
            p.add_color_stop_rgb(1, 1.0, 1.0, 1.0)
            p.add_color_stop_rgb(0, 0.5, 0.5, 1.0)

            layout = helpers.get_layout(waist, font)
            waist_rect = helpers.get_layout_rect(layout).inset(-10)
            cr.set_source(text_color)
            with helpers.save():
                cr.translate(0, 2 * tilt * 20)
                helpers.show_layout(layout, centered=True)
            cr.set_line_width(3.0)

            if fill:
                elipse(box.north(), box.width / 2, True)
            else:
                elipse(box.north(), box.width / 2, True, True)
                with helpers.save():
                    cr.scale(-1, 1)
                    cr.set_source(p)
                    cr.fill_preserve()
                helpers.move_to(box.northwest())

            helpers.line_to(waist_rect.northwest())
            helpers.line_to(waist_rect.southwest())
            helpers.line_to(box.southwest())

            elipse(box.south(), box.width / 2, False)
            helpers.line_to(waist_rect.southeast())
            helpers.line_to(waist_rect.northeast())
            helpers.line_to(box.northeast())

            if fill:
                cr.set_source(p)
                cr.fill()
            else:
                cr.set_source_rgba(0, 0, 0, 0.5)
                elipse(waist_rect.north(), waist_rect.width / 2, tilt * 20)
                elipse(waist_rect.south(), waist_rect.width / 2, tilt * 20)
                cr.stroke()

    hourglass(window.inset(20), fill=True)
    hourglass(window.inset(20), fill=False)
