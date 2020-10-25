export background_color=FF000000
export dial_color=FFFFFF00
export show_outline=false
export from_stdin=true
./fake_rpm.py | ./wayland_runner.py examples/tach.py
