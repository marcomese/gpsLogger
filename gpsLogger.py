#!/usr/bin/python3

import sys
from graphUtils import gpsPlotter

if __name__ == '__main__':
    try:
        gps = gpsPlotter()

        while True:
            gps.update()

            print(gps)
  
    except KeyboardInterrupt:
        gps.close()
        sys.exit("\nExiting...")
