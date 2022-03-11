if __name__ == "init":
    params.define("n_stars", Numeric(4, 100, 1, 11))
    params.define("n_waves", Numeric(2, 100, 1, 12))
    params.define("speed", Numeric(1/128, 2, 0.125, 0.3))
    params.define("color", Color(1, 0, 0, 0.75))
    params.define("radius", Infinite(5.0))
else:
    import time

    stars = int(n_stars)
    angle = 2 * math.pi / stars
    speed = 1 / speed
    phase_separation = speed / n_waves

    def starburst(phase):
        with helpers.box(window) as layout:
            for i in range(stars):
                with helpers.save():
                    cr.rotate(i * angle + phase)
                    helpers.circle(Point(phase * window.radius(), 0), radius)
                    cr.fill()

    cr.set_source(color)
    for i in range(int(n_waves)):
        starburst((time.time() + i * phase_separation) % speed)
