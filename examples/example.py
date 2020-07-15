import time
import math

radius = min(window.width, window.height)
n = 10
angle = 2 * math.pi / n
phase = time.time() % 1.0

def starburst(phase):
    with helpers.Box(cr, window) as layout:
        for i in range(n):
            with helpers.Save(cr):
                cr.rotate(i * angle + phase)
                cr.arc(phase * radius, 0, 10, 0, 2 * math.pi)
                cr.fill()

starburst(phase)
starburst(phase + 0.5)
