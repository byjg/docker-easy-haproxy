#!/usr/bin/env python

import os
import signal

from supervisor import childutils


def main():
    while True:
        headers, payload = childutils.listener.wait()
        childutils.listener.ok()
        events = ['PROCESS_STATE_FATAL', 'PROCESS_STATE_EXITED', 'PROCESS_STATE_STOPPED']
        if not (headers['eventname'] in events):
            continue

        print(headers)
        print(payload)
        os.kill(os.getppid(), signal.SIGTERM)


if __name__ == "__main__":
    main()
