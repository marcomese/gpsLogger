import matplotlib.pyplot as plt
import matplotlib.gridspec as grd
import numpy as np
from matplotlib.ticker import FormatStrFormatter
from mpl_toolkits.basemap import Basemap
from datetime import datetime
from time import strptime
from gpsUtils import gpsLogger
from imuUtils import imuLogger, queries

class gpsPlotter(gpsLogger, imuLogger):
    def __init__(self, localIP = "0.0.0.0", localPort = 6003):
        super(gpsPlotter, self).__init__(localIP = localIP,
                                         localPort = localPort,
                                         dbHost = 'calibano.ba.infn.it',
                                         dbPort = 8086,
                                         dbQueries = queries,
                                         database='spbmonitor',
                                         queryInterval = 2, 
                                         convHost = '127.0.0.1', 
                                         convPort = 5000,
                                         logFileName = None,
                                         bufSize = 1024)

        self._tArr = []
        self._altArr = []
        self._gpsTiltArr = []
        self._gpsYawArr = []
        self._rollArr = []
        self._pitchArr = []
        self._yawArr = []
        self._imuTArr = []
        self._quaternionsArr = []
        self._tm = 0
        self._imuTM = 0

        self._fig = plt.figure(figsize=(50, 50))
        self._grid = grd.GridSpec(2, 2)

        self._axND = plt.Subplot(self._fig, self._grid[0])
        self._axND.set_title("Current position")
        self._fig.add_subplot(self._axND)

        self._axPos = plt.Subplot(self._fig, self._grid[2])
        self._axPos.set_title("Position history")
        self._fig.add_subplot(self._axPos)

        self._gpsMeasGrid = grd.GridSpecFromSubplotSpec(3, 1, subplot_spec=self._grid[1], hspace=0.0)

        self._axAlt = plt.Subplot(self._fig, self._gpsMeasGrid[0])
        self._axAlt.set_title("GPS measurements")
        self._axAlt.set_ylabel("Altitude (m)")
        self._axAlt.ticklabel_format(axis = 'y', style='plain', useOffset=False)
        self._axAlt.yaxis.set_major_formatter(FormatStrFormatter('%.2f'))
        self._fig.add_subplot(self._axAlt)

        self._axTilt = plt.Subplot(self._fig, self._gpsMeasGrid[1], sharex=self._axAlt)
        self._axTilt.set_ylabel("GPS Tilt (degrees)")
        self._axTilt.ticklabel_format(axis = 'y', style='plain', useOffset=False)
        self._axTilt.yaxis.set_major_formatter(FormatStrFormatter('%.2f'))
        self._fig.add_subplot(self._axTilt)

        self._axYaw = plt.Subplot(self._fig, self._gpsMeasGrid[2], sharex=self._axAlt)
        self._axYaw.set_ylabel("GPS Yaw (degrees)")
        self._axYaw.ticklabel_format(axis = 'y', style='plain', useOffset=False)
        self._axYaw.yaxis.set_major_formatter(FormatStrFormatter('%.2f'))
        self._fig.add_subplot(self._axYaw)

        self._orientGrid = grd.GridSpecFromSubplotSpec(3, 1, subplot_spec=self._grid[3], hspace=0.0)

        self._axOrientRoll = plt.Subplot(self._fig, self._orientGrid[0])
        self._axOrientRoll.set_title("IMU sensor measurements")
        self._axOrientRoll.set_ylabel("Roll (degrees)")
        self._axOrientRoll.ticklabel_format(axis = 'y', style='plain', useOffset=False)
        self._axOrientRoll.yaxis.set_major_formatter(FormatStrFormatter('%.2f'))
        self._fig.add_subplot(self._axOrientRoll)

        self._axOrientPitch = plt.Subplot(self._fig, self._orientGrid[1], sharex=self._axOrientRoll)
        self._axOrientPitch.set_ylabel("Pitch (degrees)")
        self._axOrientPitch.ticklabel_format(axis = 'y', style='plain', useOffset=False)
        self._axOrientPitch.yaxis.set_major_formatter(FormatStrFormatter('%.2f'))
        self._fig.add_subplot(self._axOrientPitch)

        self._axOrientYaw = plt.Subplot(self._fig, self._orientGrid[2], sharex=self._axOrientRoll)
        self._axOrientYaw.set_ylabel("Yaw (degrees)")
        self._axOrientYaw.ticklabel_format(axis = 'y', style='plain', useOffset=False)
        self._axOrientYaw.yaxis.set_major_formatter(FormatStrFormatter('%.2f'))
        self._fig.add_subplot(self._axOrientYaw)

        self._mPos = Basemap(projection='merc',
                             llcrnrlat=-80, urcrnrlat=80,
                             llcrnrlon=-180, urcrnrlon=180,
                             lat_ts=20, ax = self._axPos)

        self._mPos.shadedrelief(scale=0.2)
        self._mPos.drawcoastlines(color='white', linewidth=0.2)
        self._mPos.drawparallels(np.arange(-90,90,30),labels=[1,0,0,0])
        self._mPos.drawmeridians(np.arange(self._mPos.lonmin,
                                           self._mPos.lonmax+30,60),
                                 labels=[0,0,0,1])

        self._mND = Basemap(projection='merc',
                            llcrnrlat=-80, urcrnrlat=80,
                            llcrnrlon=-180, urcrnrlon=180,
                            lat_ts=20, ax = self._axND)

        plt.ion()

    def _updateMap(self):
        lon = super().longitude
        lat = super().latitude

        x, y = self._mPos(lon, lat)
        date = datetime.utcnow()

        self._mND.shadedrelief(scale=0.2)
        self._mND.drawcoastlines(color='white', linewidth=0.2)
        self._mND.drawparallels(np.arange(-90,90,30),labels=[1,0,0,0])
        self._mND.drawmeridians(np.arange(self._mND.lonmin,
                                    self._mND.lonmax+30,60),
                                labels=[0,0,0,1])
        self._mND.nightshade(date, ax=self._axND)

        self._axND.set_title("Current position")
        self._axND.plot(x,y,'r.')
        
        self._axPos.plot(x,y,'r.:')

    def _refreshAxis(self, axisToRefresh):
        title = axisToRefresh.get_title()
        ylabel = axisToRefresh.yaxis.get_label().get_text()
        fmt = axisToRefresh.yaxis.get_major_formatter()
        
        axisToRefresh.cla()
        axisToRefresh.ticklabel_format(axis = 'y', style='plain', useOffset=False)
        axisToRefresh.yaxis.set_major_formatter(fmt)
        axisToRefresh.set_title(title)
        axisToRefresh.set_ylabel(ylabel)

    def _updateGPSMeas(self, timeInterval = 5, maxPoints = 5):
        currTmStr = super().time
        alt = super().altitude
        yaw = super().yaw
        tilt = super().tilt
        
        if currTmStr == '':
            return

        cTmStruct = strptime(currTmStr, "%H:%M:%S")

        currTm = (cTmStruct.tm_sec + (cTmStruct.tm_min * 60)  + (cTmStruct.tm_hour * 3600))

        if currTm == 0:
            self._tm = 0

        if (currTm - self._tm) < timeInterval:
            return

        self._tm = currTm

        if len(self._tArr) >= maxPoints:
            self._tArr.pop(0)
            self._altArr.pop(0)
            self._gpsYawArr.pop(0)
            self._gpsTiltArr.pop(0)
            self._refreshAxis(self._axAlt)
            self._refreshAxis(self._axYaw)
            self._refreshAxis(self._axTilt)

        self._tArr.append(currTmStr)
        self._altArr.append(alt)
        self._gpsYawArr.append(yaw)
        self._gpsTiltArr.append(tilt)
    
        self._axAlt.plot(self._tArr, self._altArr,'r.:')
        self._axYaw.plot(self._tArr, self._gpsYawArr,'r.:')
        self._axTilt.plot(self._tArr, self._gpsTiltArr,'r.:')

    def _updateIMUMeas(self, timeInterval = 5, maxPoints = 5):
        quats = super().quaternions
        eulers = super().eulers
        time = quats['time']

        if time == '':
            return

        cTmStruct = strptime(time, "%H:%M:%S")

        currTm = (cTmStruct.tm_sec + (cTmStruct.tm_min * 60)  + (cTmStruct.tm_hour * 3600))

        if currTm == 0:
            self._imuTM = 0

        if (currTm - self._imuTM) < timeInterval:
            return

        self._imuTM = currTm

        if len(self._imuTArr) >= maxPoints:
            self._imuTArr.pop(0)
            self._rollArr.pop(0)
            self._pitchArr.pop(0)
            self._yawArr.pop(0)
            self._quaternionsArr.pop(0)
            self._refreshAxis(self._axOrientRoll)
            self._refreshAxis(self._axOrientPitch)
            self._refreshAxis(self._axOrientYaw)

        self._imuTArr.append(time)
        self._rollArr.append(eulers['roll'])
        self._pitchArr.append(eulers['pitch'])
        self._yawArr.append(eulers['yaw'])
        self._quaternionsArr.append(quats)
        
        self._axOrientRoll.plot(self._imuTArr, self._rollArr,'r.:')
        self._axOrientPitch.plot(self._imuTArr, self._pitchArr,'r.:')
        self._axOrientYaw.plot(self._imuTArr, self._yawArr,'r.:')

    def update(self):
        self.updateGPS()
        self.updateIMU()
        
        self._updateMap()
        self._updateGPSMeas()
        self._updateIMUMeas()

        plt.draw()
        plt.pause(0.001)

        self._axND.cla()

    def __str__(self):
        return super(gpsPlotter, self).__str__()
