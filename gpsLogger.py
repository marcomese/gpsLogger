#!/usr/bin/python3

import sys
from graphUtils import gpsPlotter

if __name__ == '__main__':
    try:
        gps = gpsPlotter()

        while True:
            gps.updateMap()

            print(gps)
  
    except KeyboardInterrupt:
        gpsLog.close()
        sys.exit("\nExiting...")
