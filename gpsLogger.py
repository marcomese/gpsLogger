#!/usr/bin/python3

import sys
from gpsUtils import gpsLogger
from graphUtils import initGraph, plotMap

if __name__ == '__main__':
    try:
        gps = gpsLogger()
        
        fig, axND, axPos, mND, mPos = initGraph()

        while True:
            gps.update()

            plotMap(gps.longitude, gps.latitude,
                    axND, axPos, 
                    mND, mPos)

            print(f"T = {gps.time} "
                  f"LONG = {gps.longitude:.3f} "
                  f"LAT = {gps.latitude:.3f} "
                  f"YAW = {gps.yaw:.3f} "
                  f"TILT = {gps.tilt:.3f}")
  
    except KeyboardInterrupt:
        gps.close()
        sys.exit("\nExiting...")
