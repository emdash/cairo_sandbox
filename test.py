import sys
import logging
from watchdog.observers import Observer
from watchdog.events import LoggingEventHandler
import os
from time import sleep

def on_any_event(event):
    print(event)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO,
            format='%(asctime)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S')
    path = sys.argv[1]
    event_handler = LoggingEventHandler()
    event_handler.on_any_event = on_any_event
    observer = Observer()
    dir = os.path.split(path)[0]
    observer.schedule(event_handler, dir, recursive=True)
    observer.start()

    sleep(1000)
