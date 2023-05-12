import sys, socket, re
from time import sleep, gmtime, strptime
from influxdb import InfluxDBClient
from itertools import zip_longest

quatQuery = ("SELECT \"instance\", \"value\" FROM \"HKB\" "
             "WHERE (\"metric\" = 'quaternions' "
             "AND time > now()-{}s)")

rawGyroQuery = ("SELECT \"instance\", \"value\" FROM \"HKB\" "
                "WHERE (\"metric\" = 'position' "
                "AND time > now()-{}s)")

rawAccelQuery = ("SELECT \"instance\", \"value\" FROM \"HKB\" "
                 "WHERE (\"metric\" = 'acceleration' "
                 "AND time > now()-{}s)")

queries = {'quat'  : {'query'     : quatQuery, 
                      'instances' : ['q1','q2','q3','q4'],
                      'toSigned'  : False},
           'accel' : {'query'     : rawAccelQuery,
                      'instances' : ['X','Y','Z'],
                      'toSigned'  : True},
           'gyro'  : {'query'     : rawGyroQuery,
                      'instances' : ['X','Y','Z'],
                      'tSigned'   : True}}

numericPattern = "([-+]?[0-9]*\.?[0-9]+(?:[eE][-+]?[0-9]+)*)"
convQuatPattern = (f"Q{numericPattern},{numericPattern},"
                    f"{numericPattern},{numericPattern}E")
convQuatRegex = re.compile(convQuatPattern)

class imuLogger(object):
    def __init__(self, dbHost = 'calibano.ba.infn.it', dbPort = 8086,
                 dbQueries = queries, database='spbmonitor',
                 timeInterval = 2,
                 convHost = '127.0.0.1', convPort = 5000,
                 logFileName = None, bufSize = 1024):
        self._dbClient = InfluxDBClient(host=dbHost, 
                                        port=dbPort,
                                        database=database)

        self._tm = gmtime()
        self._timeInterval = timeInterval
        self._bufSize = bufSize
        self._packets = []
        self._length = 0
        self._dbQueries = dbQueries
        self._imuConv = None
        # results from db queries
        self._imuResults = {qN : None for qN in queries.keys()}
        # results from converter
        self._imuResults.update({'convQuat' : None,
                                 'euler'    : None})

        self._logFileName = (f"{logFileName}-{self._tm.tm_year}"
                             f"{self._tm.tm_mon}{self._tm.tm_mday}-"
                             f"{self._tm.tm_hour}{self._tm.tm_min}"
                             f"{self._tm.tm_sec}.dat")

        if convHost is not None:
            imuConvSocket = socket.socket(socket.AF_INET,
                                          socket.SOCK_STREAM)
            
            welcomeStr = b''
            if imuConvSocket is not None:
                imuConvSocket.connect((convHost, convPort))
                welcomeStr = imuConvSocket.recv(bufSize)
            
            if welcomeStr == b'Imu conv':
                print("Imu converter ready")
                
                self._imuConv = imuConvSocket

    @property
    def accel(self):
        return self._imuResults['accel']

    @property
    def gyro(self):
        return self._imuResults['gyro']

    @property
    def quaternions(self):
        return self._imuResults['quat']

    @property
    def eulers(self):
        return self._imuResults['euler']

    @property
    def results(self):
        return self._imuResults

    def _toSigned(n,bits):
        n = n & (2**bits)-1
        return n | (-(n & (1 << (bits-1))))

    def _getTime(self, timeStr, fmt = "%Y-%m-%dT%H:%M:%S.%f"):
            cT = timeStr.split('.')

            # on linux the decimal part of seconds cannot be > 6 digits
            uS = cT[1][:6]

            cT = cT[0]+'.'+uS

            return strptime(cT, fmt)

    def _getCmpltSeq(self, sequence, instances, keyword = 'instance'):
        retVal = []
        i = 0
        j = 0
        t0 = None
        seq = sequence.copy()

        while(i < len(sequence)):
            s = seq.pop(0)

            t1 = self._getTime(s['time'])

            if s[keyword] != instances[j]:
                i = i + 1
                continue

            if t0 is None:
                t0 = self._getTime(s['time'])

            i = i + 1
            j = (j + 1)%len(instances)

            retVal.append(s)

            if ((s[keyword] == instances[-1]) and 
                (t1.tm_sec - t0.tm_sec <= 1.0)):
                yield retVal

    def update(self):
        quatsArr = None
        gyroArr = None
        accelArr = None
        comptQuats = None
        
        qRes = {}
        for tN,tQ in self._dbQueries.items():
            q = tQ['query'].format(self._timeInterval)
            qR = list(self._dbClient.query(q).get_points())
            qRes = [q for q in self._getCmpltSeq(qR, tQ['instances'])]

            print(f"q = {q} qR = {qR} qRes = {qRes}")

            if qRes != []:
                self._imuResults.update({tN : qRes})

        if self._imuConv is None:
            return
        
        accelRes = self._imuResults['accel']
        gyroRes = self._imuResults['gyro']
        if (accelRes is not None) and (gyroRes is not None):
            for acc,gyr in zip_longest(accelRes, gyroRes):
                accelStr = ','.join([str(a or '') for a in acc])
                gyroStr = ','.join([str(g or '') for g in gyr])

                strToSend = f"{gyroStr},{accelStr}\n".encode('utf-8')
                self._imuConv.send(strToSend)

                recD = self._imuConv.recv(self._bufSize).decode('utf-8')
                quatFound = convQuatRegex.findall(recD)

                if quatFound is not None:
                    quatResDict = {'convQuat' :
                                   [float(q) for q in quatFound[0]]}
                    self._imuResults.update(quatResDict)

    def __str__(self):
        return (f"ACCEL = {self.accel} "
                f"GYRO = {self.gyro} "
                f"QUATERNIONS = {self.quaternions}")

    def __del__(self):
        if self._imuConv is not None:
            self._imuConv.close()
        if self._dbClient is not None:
            self._dbClient.close()

    def close(self):
        if self._imuConv is not None:
            self._imuConv.close()
        if self._dbClient is not None:
            self._dbClient.close()

if __name__ == "__main__":
    try:
        imuLog = imuLogger()
    
        while True:
            imuLog.update()
            print(imuLog) 
    except KeyboardInterrupt:
        imuLog.close()
        sys.exit("\nExiting...")
