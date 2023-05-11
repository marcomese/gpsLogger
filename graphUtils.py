import matplotlib.pyplot as plt
import numpy as np
from mpl_toolkits.basemap import Basemap
from datetime import datetime

class gpsPlotter(object):
    def __init__(self):
        self._fig, (self._axND, self._axPos) = plt.subplots(2,figsize=(50,50))

        self._axPos.set_title("Position history")

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

    def updateMap(self, longitude, latitude):
        x, y = self._mPos(longitude, latitude)
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
        
        self._axPos.plot(x,y,'r.')
        
        plt.draw()
        plt.pause(0.001)

        self._axND.cla()
