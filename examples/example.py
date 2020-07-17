if __name__ == "init":
    params.define("n_stars", Numeric(4, 100, 1, 11))
    params.define("n_waves", Numeric(2, 100, 1, 12))
    params.define("speed", Numeric(0, 2, 0.125, 0.3))
    params.define("color", Color(1, 0, 0, 0.75))
else:
    import time
    
    radius = min(window.width, window.height)
    stars = int(params["n_stars"])
    angle = 2 * math.pi / stars
    speed = 1 / params["speed"]
    phase_separation = speed / params["n_waves"]
    
    def starburst(phase):
        with helpers.box(window) as layout:
            for i in range(stars):
                with helpers.save():
                    cr.rotate(i * angle + phase)
                    cr.arc(phase * radius, 0, 10, 0, 2 * math.pi)
                    cr.fill()

        
    cr.set_source(params["color"])
    for i in range(int(params["n_waves"])):
        starburst((time.time() + i * phase_separation) % speed)
    
