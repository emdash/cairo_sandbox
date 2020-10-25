#!/usr/bin/python3

import time
import math
import json
import sys

while True:
    print(json.dumps({
        "rpm": 6500 * 0.5 * (1 + math.sin(time.time()))
    }))
    time.sleep(0.025)
    sys.stdout.flush()
