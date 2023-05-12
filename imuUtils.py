import sys, socket, re
from time import sleep, gmtime, strptime
from influxdb import InfluxDBClient

quatQuery = """SELECT "instance", "value" FROM "HKB" 
                  WHERE ("metric" = 'quaternions' AND 
                         time > now()-{}s)"""

rawGyroQuery = """SELECT "instance", "value" FROM "HKB" 
                  WHERE ("metric" = 'position' AND time > now()-{}s)"""

rawAccelQuery = """SELECT "instance", "value" FROM "HKB" 
                   WHERE ("metric" = 'acceleration' AND time > now()-{}s)"""

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
comptQuatPattern = (f"Q{numericPattern},{numericPattern},"
                    f"{numericPattern},{numericPattern}E")
comptQuatRegex = re.compile(comptQuatPattern)

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
        self._packets = []
        self._length = 0
        self._dbQueries = dbQueries
        self._imuConv = None
        # results from db queries
        self._imuResults = {qN : None for qN in queries.keys()}
        # results from converter
        self._imuResults.update({'euler' : None})

        self._logFileName = (f"{logFileName}-{self._tm.tm_year}"
                             f"{self._tm.tm_mon}{self._tm.tm_mday}-"
                             f"{self._tm.tm_hour}{self._tm.tm_min}"
                             f"{self._tm.tm_sec}.dat")

        if convHost is not None:
            imuConvSocket = socket.socket(socket.AF_INET,
                                          socket.SOCK_STREAM)
            
            welcomeStr = b''
            if imuConvSocket is not None:
                imuConvSocket.connect((imuConvHost, convPort))
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

    def _toSigned(n,bits):
        n = n & (2**bits)-1
        return n | (-(n & (1 << (bits-1))))

    def _getTime(timeStr, fmt = "%Y-%m-%dT%H:%M:%S.%f"):
            cT = timeStr.split('.')

            # on linux the decimal part of seconds cannot be > 6 digits
            uS = cT[1][:6]

            cT = cT[0]+'.'+uS

            return strptime(cT, fmt)

    def _getCompleteSequence(sequence, instances, keyword = 'instance'):
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
            qRes = [q for q in self._getCompleteSequence(qR, tQ['instances'])]

            if qRes != []:
                self._imuResults.update{tN : qRes}

        if subSeq is not None:
            quatsArr = [q['value'] for q in subSeq]

        gyroStr = ""
        if gyroSubSeq is not None:
            gyroArr = [toSigned(int(g['value']),16) for g in gyroSubSeq]
            gyroStr = f"{gyroArr[0]},{gyroArr[1]},{gyroArr[2]}"

        accelStr = ""
        if accelSubSeq is not None:
            accelArr = [toSigned(int(a['value']),16) for a in accelSubSeq]
            accelStr = f"{accelArr[0]},{accelArr[1]},{accelArr[2]}"

        if self.imuConv is not None and gyroStr != "" and accelStr != "":
            self.imuConv.send(f"{gyroStr},{accelStr}\n".encode('utf-8'))

            recvData = self.imuConv.recv(1024)

            comptQuatsFound = comptQuatRegex.findall(recvData.decode('utf-8'))

            if comptQuatsFound is not None:
                comptQuats = [float(q) for q in comptQuatsFound[0]]

        self.quatsArr = quatsArr
        self.comptQuats = comptQuats

        self.quat_delegate.dispatch((quatsArr,gyroArr,accelArr,comptQuats))

    def __str__(self):
        return (f"ACCEL = ({self.accel[0]},{self.accel[1]},{self.accel[2]}) "
                f"GYRO = ({self.gyro[0]},{self.gyro[1]},{self.gyro[2]}) "
                f"QUATERNIONS = ({self.quaternions[0]},{self.quaternions[1]}"
                f",{self.quaternions[2]},{self.quaternions[3]})")
