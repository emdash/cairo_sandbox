import sys
import logging
from watchdog.observers import Observer
from watchdog.events import LoggingEventHandler
import os

def on_any_event(event):
    print(event)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO,
            format='%(asctime)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S')
    path = '/Users/charlie/src/uDashStuff/cairo_sandbox/examples/'
    event_handler = LoggingEventHandler()
    event_handler.on_any_event = on_any_event
    observer = Observer()
    dir = os.path.split(path)[0]
    observer.schedule(event_handler, dir, recursive=True)
    observer.start()
    try:
        print("Monitoring")
        while observer.isAlive():
            observer.join(1)
    except KeyboardInterrupt:
            observer.stop()
            print("Done")
    observer.join()
