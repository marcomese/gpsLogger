import re
from numpy import nan
import socket

numericPattern = "[+-]?[0-9]*\.?[0-9]+"

gpsPattern = "(gps1|gps2),\s*(.*)"
gpsRegex = re.compile(gpsPattern)

gpsDataPattern = "(\d*),"
gpsDataRegex = re.compile(gpsDataPattern)

orientationPattern = (f"\$PTNL,AVR,(?:{numericPattern}),"
                      f"({numericPattern}),Yaw,({numericPattern}),Tilt")
orientationRegex = re.compile(orientationPattern)

positionPattern = (f"\$GPGGA,({numericPattern})," # timestamp
                   f"({numericPattern}),(N|S),"   # latitude
                   f"({numericPattern}),(W|E),"   # longitude
                   f"({numericPattern}),"         # fix quality
                   f"({numericPattern}),"         # number of satellites
                   f"({numericPattern}),"         # hdop
                   f"({numericPattern}),M")       # altitude
positionRegex = re.compile(positionPattern)

gpsTimePattern = "(\d\d)(\d\d)(\d\d).00"
gpsTimeRegex = re.compile(gpsTimePattern)

class gpsLogger(object):
    def __init__(self, localIP = "0.0.0.0", localPort = 6003, 
                 bufSize = 1024, *args, **kwargs):
        super(gpsLogger, self).__init__(*args, **kwargs)

        self._netlogger = socket.socket(family=socket.AF_INET,
                                        type=socket.SOCK_DGRAM)
        
        if self._netlogger is not None:
            self._netlogger.bind((localIP, localPort))
        
        self._bufSize = bufSize
        self._lastMsgAddrPair = None
        self._lastMsg = None
        self._lastAddr = None
        self._lastTime = ""
        self._lastLong = nan
        self._lastLat = nan
        self._lastYaw = nan
        self._lastTilt = nan
        self._lastAlt = nan
        self._lastGPS = None

    @property
    def time(self):
        return self._lastTime

    @property
    def longitude(self):
        return self._lastLong

    @property
    def latitude(self):
        return self._lastLat

    @property
    def yaw(self):
        return self._lastYaw

    @property
    def tilt(self):
        return self._lastTilt

    @property
    def altitude(self):
        return self._lastAlt

    def _collectGPSData(self):
        if self._netlogger is not None:
            self._lastMsgAddrPair = self._netlogger.recvfrom(self._bufSize)

        if self._lastMsgAddrPair is not None:
            self._lastMsg = self._lastMsgAddrPair[0].decode('utf-8')
            self._lastAddr = self._lastMsgAddrPair[1]

    def updateGPS(self):
        gpsTimeStr = ""
        longitude = nan
        latitude = nan
        yaw = nan
        tilt = nan

        self._collectGPSData()

        gpsData = gpsRegex.findall(self._lastMsg)

        for g in gpsData:
            gpsStr = g[1].replace('\n',' ')
            
            self._lastGPS = g[0].upper()

            gpsOrientData = orientationRegex.findall(gpsStr)
            if gpsOrientData != []:
                data = gpsOrientData[0]
                yaw = float(data[0] or nan)
                tilt = float(data[1] or nan)
                self._lastYaw  = yaw
                self._lastTilt = tilt

            gpsPositionData = positionRegex.findall(gpsStr)
            if gpsPositionData != []:
                data = gpsPositionData[0]
                gpsTime = gpsTimeRegex.findall(data[0])[0]
                gpsTimeStr = f"{gpsTime[0]}:{gpsTime[1]}:{gpsTime[2]}"

                latSig = -1 if data[2] == 'S' else 1
                latitude = latSig*float(data[1] or nan)/100.0
                
                longSig = -1 if data[4] == 'W' else 1
                longitude = longSig*float(data[3] or nan)/100.0

                altitude = float(data[8] or nan)

                self._lastTime = gpsTimeStr
                self._lastLong = longitude
                self._lastLat  = latitude
                self._lastAlt  = altitude

    def __str__(self):
        return (f"({self._lastGPS}) "
                f"T = {self._lastTime} "
                f"LONG = {self._lastLong:.5f} "
                f"LAT = {self._lastLat:.5f} "
                f"YAW = {self._lastYaw:.3f} "
                f"TILT = {self._lastTilt:.3f} "
                f"ALTITUDE = {self._lastAlt:.3f}")

    def close(self):
        self._netlogger.close()
