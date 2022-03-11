import math
import cmath
if __name__ == 'init':
    params.define("left_arm_angle", Angle(default=1.62))
    params.define("right_arm_angle", Angle(default=1.55))
    params.define("left_elbo_angle", Angle(default=4.42))
    params.define("right_elbo_angle", Angle(default=1.63))
    params.define("left_hip_angle", Angle(default=1.76))
    params.define("right_hip_angle", Angle(default=1.46))
    params.define("left_knee_angle", Angle(default=1.55))
    params.define("right_knee_angle", Angle(default=1.55))
    params.define("height", Infinite(80))
    params.define("arm_length", Infinite(25))
    params.define("thigh_length", Infinite(28))
    params.define("calf_length", Infinite(46))
else:
    head_center = Point(window.center.x, 25)
    pelvis_center = head_center + Point(0, height)
    shoulder_center = head_center + Point(0, 35)
    left_shoulder = shoulder_center + Point(-20, 5)
    right_shoulder = shoulder_center + Point(20, 5)
    left_elbo = left_shoulder + Point.from_polar(arm_length, left_arm_angle)
    right_elbo = right_shoulder + Point.from_polar(arm_length, right_arm_angle)
    left_wrist = left_elbo + Point.from_polar(arm_length * 1.2, left_elbo_angle)
    right_wrist = right_elbo + Point.from_polar(arm_length * 1.2, right_elbo_angle)
    left_hip = pelvis_center + Point(-15, 0)
    right_hip = pelvis_center + Point(15, 0)
    left_knee = left_hip + Point.from_polar(thigh_length, left_hip_angle)
    right_knee = right_hip + Point.from_polar(thigh_length, right_hip_angle)
    left_ankle = left_knee + Point.from_polar(calf_length, left_knee_angle)
    right_ankle = right_knee + Point.from_polar(calf_length, right_knee_angle)

    white = cairo.SolidPattern(1, 1, 1)
    black = cairo.SolidPattern(0, 0, 0)

    def fill_stroke(fill_color):
        cr.set_source(fill_color)
        cr.fill_preserve()
        cr.set_source(black)
        cr.stroke()

    # spine
    helpers.move_to(head_center)
    helpers.line_to(pelvis_center)
    cr.stroke()

    # head
    helpers.elipse(head_center, 12, 15)
    fill_stroke(white)

    # shoulders
    helpers.move_to(shoulder_center)
    helpers.line_to(left_shoulder)
    helpers.line_to(left_elbo)
    helpers.line_to(left_wrist)
    cr.stroke()
    helpers.circle(left_wrist, 5)
    fill_stroke(white)

    helpers.move_to(shoulder_center)
    helpers.line_to(right_shoulder)
    helpers.line_to(right_elbo)
    helpers.line_to(right_wrist)
    cr.stroke()
    helpers.circle(right_wrist, 5)
    fill_stroke(white)

    #torso
    helpers.move_to(left_hip)
    helpers.line_to(right_hip)
    cr.stroke()

    # legs
    helpers.move_to(left_hip)
    helpers.line_to(left_knee)
    helpers.line_to(left_ankle)
    cr.stroke()
    helpers.circle(left_ankle, 7)
    fill_stroke(white)

    helpers.move_to(right_hip)
    helpers.line_to(right_knee)
    helpers.line_to(right_ankle)
    cr.stroke()
    helpers.circle(right_ankle, 7)
    fill_stroke(white)

