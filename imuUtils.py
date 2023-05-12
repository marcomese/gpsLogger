import sys, socket, re
from time import gmtime, strptime
from influxdb import InfluxDBClient
from numpy import nan

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
                      'toSigned'  : None},
           'accel' : {'query'     : rawAccelQuery,
                      'instances' : ['X','Y','Z'],
                      'toSigned'  : 16},
           'gyro'  : {'query'     : rawGyroQuery,
                      'instances' : ['X','Y','Z'],
                      'toSigned'  : 16}}

numericPattern = "([-+]?[0-9]*\.?[0-9]+(?:[eE][-+]?[0-9]+)*)"
convPattern = (f"Q{numericPattern},{numericPattern},"
               f"{numericPattern},{numericPattern}"
               f"E{numericPattern},{numericPattern},"
               f"{numericPattern}")
convRegex = re.compile(convPattern)

iToE = {0:'roll',
        1:'pitch',
        2:'yaw'}

class imuLogger(object):
    def __init__(self, dbHost = 'calibano.ba.infn.it', dbPort = 8086,
                 dbQueries = queries, database='spbmonitor',
                 queryInterval = 2, 
                 convHost = '127.0.0.1', convPort = 5000,
                 logFileName = None, bufSize = 1024,
                 *args, **kwargs):
        super(imuLogger, self).__init__(*args, **kwargs)

        self._dbClient = InfluxDBClient(host=dbHost, 
                                        port=dbPort,
                                        database=database)

        self._initTime = gmtime()
        self._queryInterval = queryInterval
        self._bufSize = bufSize
        self._dbQueries = dbQueries
        self._imuConv = None
        # results from db queries
        self._imuResults = {qN : {k : nan for k in qV['instances']} 
                            for qN, qV in queries.items()}
        # results from converter
        self._imuResults.update({'convQuat' : {f"q{i+1}" : nan
                                               for i in range(4)},
                                 'euler'    : {iToE[i] : nan
                                               for i in range(3)}})

        self._logFileName = (f"{logFileName}-"
                             f"{self._initTime.tm_year}"
                             f"{self._initTime.tm_mon}"
                             f"{self._initTime.tm_mday}-"
                             f"{self._initTime.tm_hour}"
                             f"{self._initTime.tm_min}"
                             f"{self._initTime.tm_sec}.dat")

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
    def convQuaternions(self):
        return self._imuResults['convQuat']

    @property
    def eulers(self):
        return self._imuResults['euler']

    @property
    def results(self):
        return self._imuResults

    def _toSigned(self, n, bits):
        if bits is None:
            return n

        n = n & (2**bits)-1
        
        return n | (-(n & (1 << (bits-1))))

    def _getTime(self, timeStr, fmt = "%Y-%m-%dT%H:%M:%S.%f"):
            cT = timeStr.replace('Z','').split('.')

            # on linux the decimal part of seconds cannot be > 6 digits
            uS = cT[1][:6]

            cT = cT[0]+'.'+uS

            return strptime(cT, fmt)

    def _getCmpltSeq(self, sequence, instances,
                     keyword = 'instance', toSigned = None):
        retVal = {k : None for k in instances}
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

            val = self._toSigned(s['value'], toSigned)

            retVal.update({s[keyword] : val})

            if ((s[keyword] == instances[-1]) and 
                (t1.tm_sec - t0.tm_sec <= 1.0)):
                hours = t1.tm_hour
                mins = t1.tm_min
                secs = t1.tm_sec

                timeStr = f"{hours:02d}:{mins:02d}:{secs:02d}"

                retVal.update({'time' : timeStr})

                return retVal

        return None

    def updateIMU(self):
        qRes = {}
        for tN,tQ in self._dbQueries.items():
            q = tQ['query'].format(self._queryInterval)
            qR = list(self._dbClient.query(q).get_points())
            qRes = self._getCmpltSeq(qR, tQ['instances'],
                                     toSigned = tQ['toSigned'])

            if qRes is not None:
                self._imuResults.update({tN : qRes})

        if self._imuConv is None:
            return
        
        accelRes = self._imuResults['accel']
        gyroRes = self._imuResults['gyro']

        if (accelRes is not None) and (gyroRes is not None):
            accelStr = f"{accelRes['X']},{accelRes['Y']},{accelRes['Z']}"
            gyroStr = f"{gyroRes['X']},{gyroRes['Y']},{gyroRes['Z']}"

            strToSend = f"{gyroStr},{accelStr}\n".encode('utf-8')

            self._imuConv.send(strToSend)

            recD = self._imuConv.recv(self._bufSize).decode('utf-8')
            imuConvData = convRegex.findall(recD)

            if imuConvData is not None:
                convQuatDict = {f"q{i+1}":float(q or nan) 
                                for i,q in enumerate(imuConvData[0][:4])}
                
                eulersDict = {iToE[i]:float(e or nan) 
                              for i,e in enumerate(imuConvData[0][4:7])}
                
                convResDict = {'convQuat' : convQuatDict,
                               'euler'    : eulersDict}
                self._imuResults.update(convResDict)

    def __str__(self):
        return (f"ACCEL = ({self.accel['X']},"
                f"{self.accel['Y']},"
                f"{self.accel['Z']}) "
                f"GYRO =  ({self.gyro['X']},"
                f"{self.gyro['Y']},"
                f"{self.gyro['Z']}) "
                f"QUATERNIONS = ({self.quaternions['q1']},"
                f"{self.quaternions['q2']},"
                f"{self.quaternions['q3']},"
                f"{self.quaternions['q4']}) "
                f"CONV_QUAT = ({self.convQuaternions['q1']},"
                f"{self.convQuaternions['q2']},"
                f"{self.convQuaternions['q3']},"
                f"{self.convQuaternions['q4']}) "
                f"EULERS = ({self.eulers['roll']},"
                f"{self.eulers['pitch']},"
                f"{self.eulers['yaw']})")

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
