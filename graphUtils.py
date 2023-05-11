import matplotlib.pyplot as plt
import numpy as np
from mpl_toolkits.basemap import Basemap
from datetime import datetime

def initGraph():
        fig, (axND, axPos) = plt.subplots(2,figsize=(50,50))

        axPos.set_title("Position history")

        mPos = Basemap(projection='merc',
                       llcrnrlat=-80, urcrnrlat=80,
                       llcrnrlon=-180, urcrnrlon=180,
                       lat_ts=20, ax = axPos)

        mPos.shadedrelief(scale=0.2)
        mPos.drawcoastlines(color='white', linewidth=0.2)
        mPos.drawparallels(np.arange(-90,90,30),labels=[1,0,0,0])
        mPos.drawmeridians(np.arange(mPos.lonmin,mPos.lonmax+30,60),labels=[0,0,0,1])

        mND = Basemap(projection='merc',
                      llcrnrlat=-80, urcrnrlat=80,
                      llcrnrlon=-180, urcrnrlon=180,
                      lat_ts=20, ax = axND)

        plt.ion()
        
        return fig, axND, axPos, mND, mPos


def plotMap(longitude, latitude, axND, axPos, mND, mPos):
    x, y = mPos(longitude, latitude)
    date = datetime.utcnow()

    mND.shadedrelief(scale=0.2)
    mND.drawcoastlines(color='white', linewidth=0.2)
    mND.drawparallels(np.arange(-90,90,30),labels=[1,0,0,0])
    mND.drawmeridians(np.arange(mND.lonmin,mND.lonmax+30,60),labels=[0,0,0,1])
    mND.nightshade(date, ax=axND)

    axND.set_title("Current position")
    axND.plot(x,y,'r.')
    
    axPos.plot(x,y,'r.')
    
    plt.draw()
    plt.pause(0.001)

    axND.cla()
    
    return x, y, axND, axPos, mND, mPos

