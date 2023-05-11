#!/usr/bin/python3

import sys
from gpsUtils import gpsLogger
from graphUtils import gpsPlotter

if __name__ == '__main__':
    try:
        gpsLog = gpsLogger()
        
        gpsPlt = gpsPlotter()

        while True:
            gpsLog.update()

            gpsPlt.updateMap(gpsLog.longitude, gpsLog.latitude)

            print(f"T = {gpsLog.time} "
                  f"LONG = {gpsLog.longitude:.3f} "
                  f"LAT = {gpsLog.latitude:.3f} "
                  f"YAW = {gpsLog.yaw:.3f} "
                  f"TILT = {gpsLog.tilt:.3f}")
  
    except KeyboardInterrupt:
        gpsLog.close()
        sys.exit("\nExiting...")
