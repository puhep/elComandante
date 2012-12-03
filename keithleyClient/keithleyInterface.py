import time
import serial
from string import maketrans
from collections import deque
ON=1
OFF=0


class keithleyInterface:
    def __init__(self,serialPortName):
        self.bOpen=False
        self.serialPortName=serialPortName
        self.writeSleepTime=0.1
        self.readSleepTime=0.2
        self.baudrate = 57600
        self.commandEndCharacter='\r\n'
        self.removeCharacters = '\r\n\x00\x13\x10'
        self.measurments = deque()
        self.lastVoltage = 0
        self.openSerialPort()

    
    def openSerialPort(self):
        try:
            self.serial = serial.Serial(
                                        port=self.serialPortName,
                                        baudrate=57600, 
                                        parity=serial.PARITY_NONE,
                                        stopbits=serial.STOPBITS_ONE,
                                        bytesize=serial.EIGHTBITS,
                                        timeout=1
            )
            self.bOpen=True
            print 'Open serial port: \'%s\''%self.serialPortName
        except:
            print 'Could not open serial Port: \'%s\''%self.serialPortName
            self.bOpen=False
            pass
        
        self.initKeithley()
 
    def getLastVoltage(self):
        return self.lastVoltage
    
    def write(self,data):
        data+=self.commandEndCharacter
        if self.bOpen:
            output = self.serial.write(data)
        else:
            print 'Writing: %s'%data
            output = True
        time.sleep(self.writeSleepTime)
        print '%s: %s'%(output,data)
        return output==len(data)

    def read(self,minLength=1):
        out=''
        i=0
        #print  self.serial.inWaiting()
        if not self.bOpen:
            print 'cannot read since Not serial port is not open'
            return ''
        while self.serial.inWaiting()<=0 and i<10:
            time.sleep(self.readSleepTime)
            i+=1
        ts =time.time()
        maxTime = 20
        k=0
        #print "start reading %s data at %s"%(minLength,ts)
        while len(out)<minLength and time.time()-ts<maxTime:
            while self.serial.inWaiting() > 0 and time.time()-ts<maxTime:
                out += self.serial.read(1)
                self.serial.inWaiting()
                k+=1
        if time.time()-ts>maxTime:
            print "Tried reading for %s seconds."%(time.time()-ts)
            return ''
        #print 'received after %s/%s tries: %s'%(i,k,out)
        return out
        
    def isOpen(self): #OK
        if not self.bOpen:
            return False
        return self.serial.isOpen()
    
    def getSerialPort(self): #OK, but extend to compare with self.serial.port
        return self.serialPortName
    
    def reset(self):#ok
        return self.write('*RST')
    
    def setBeeper(self,status):#ok
        data = ':SYST:BEEP:STAT '
        if status==True:
            data+='ON'
        else:
            data+='OFF'
        return self.write(data)

    def enableControlBeeper(self): #ok
        return self.setBeeper(ON)
    
    def disableControlBeeper(self):#ok
        return self.setBeeper(OFF)
        
    def setOutput(self,status):#ok
        printVal =  'set Output to '
        data = ':OUTP '
        if status==True:
            data+='ON'
            printVal += 'ON'
        else:
            data+='OFF'
            printVal += 'OFF'
        print printVal
        return self.write(data)
    
    def getOutputStatus(self):
        print 'Get Output Status'
        data = ':OUTP?'
        answer = self.getAnswerForQuery(data)
        print 'length ',len(answer)
        while len(answer)>1 and not self.is_number(answer):
            answer= self.getAnswerForQuery(data)
        print answer
        if len(answer)>0 and not answer=='':
            stat = int(answer)
        else:
            stat = -1
        return stat
    
    def setComplianceAbortLevel(self,abortLevel):
        if abortLevel not in ['NEVER','EARLY','LATE']:
            return False
        self.write(':SOURCE:SWEEP:CABort %s'%abortLevel)
        
    def clearBuffer(self):
        if self.bOpen:
            print 'clearing Buffer: %s'%self.serial.inWaiting()
            while self.serial.inWaiting():
                self.read()
                time.sleep(self.readSleepTime)
        else:
            pass
            
        return self.write(':TRAC:CLEAR')
    
    def setRearOutput(self,status=True):#ok
        if status == True:
            return self.write(':ROUT:TERM REAR')
        else:
            return self.write(':ROUT:TERM FRONT')
            
    def setFixedVoltMode(self):#ok
        return self.write(':SOUR:VOLT:MODE FIX')
            
    def clearErrorQueue(self):#ok
        return self.write('*CLS')
        
    
    def setTriggerCounter(self,nTrig):
        print 'set Trigger Counter: %s'%nTrig
        if nTrig<1 or nTrig>= 2500:
            print 'Trigger Counter is not in allowed range',nTrig
            return -1
        return self.write(':TRIG:COUN %s'%int(nTrig))
        
    def setVoltageSweepStartValue(self,startValue):
        if not self.validVoltage(startValue):
            return -1
        return self.write(':SOUR:VOLT:START %s'%startValue)
        
    def setVoltageSweepStopValue(self,stopValue):
        stopVoltage=float(stopValue)
        if not self.validVoltage(stopVoltage):
            return -1
        return self.write(':SOUR:VOLT:STOP %s'%stopVoltage)
        
    def setVoltageSweepStepValue(self,stepValue):
        stepVoltage = float(stepValue)
        if not self.validVoltage(stepVoltage):
            print 'invalid sweepStepValue: ',stepVoltage
            return -1
        return self.write(':SOUR:VOLT:STEP %s'%stepVoltage)
    
    def setVoltage(self,value):
        if not self.validVoltage(value):
            print 'invalid Voltage: %s'%value
            return -1
        return self.write(':SOUR:VOLT %s'%value)
        
    def setStandardOutputForm(self):
        return self.write(':FORM:ELEM VOLT,CURR,RES,TIME,STAT')
        
    def setConcurrentMeasurments(self,value=True):
        if value==True:
            retVal =  self.write(':FUNC:CONC ON')
            retVal *=  self.write(':SENS:FUNC \'VOLT:DC\'')
#            retVal *= self.write(':SENS:FUNC \'RESISTANCE\'')
            retVal *= self.write(':SENS:FUNC \'CURR:DC\'')
            out = self.getAnswerForQuery(':SENS:FUNC?')
            print out
            return retVal
        else:
            return self.write(':FUNC:CONC OFF')
    
    
    def setDigitalFilterType(self,filterType):
        if filterType not in ['MOV','REP']:
            raise Exception('invalid filterType: %s'%filterType)
        return self.write(':SENS:AVER:TCON %s'%filterType)
    
    def setAverageFiltering(self,status=True):
        if status==True:
            return self.write(':SENS:AVER:STAT ON')
        return self.write('SENS:AVER:STAT OFF')
        
    def setAverageFilterCount(self,count):
        if count>100 or count<1:
            raise Exception('Average Filter Count not in valif rage: %s'%count)
        return self.write(':SENS:AVER:COUN %s'%count)
    
    def setCurrentProtection(self,value):
        if not self.validCurrent(value):
            raise Exception('setting currentProtection: not valid current: %s'%value)
        return self.write(':CURR:PROT:LEV %s'%value)
    
    def setCurrentMeasurmentSpeed(self,value):
        if value <0.01 or value >10:
            raise Exception ('Current NPLC not valid: %s'%value)
        return self.write(':SENS:CURR:NPLC %s'%value)
        
    def setImmidiateVoltage(self,value):
        if not self.validVoltage(value):
            raise Exception('immidiateVoltage not valid: %s'%value)
        return self.write('SOUR:VOLT:IMM:AMPL %s'%value)#TODO Do I need scientific fomat?
        
    def setMeasurementDelay(self,delay):
        if delay <0 or delay >999.9999:
            raise Exception('measurmentdelay is out of range: %s'%delay)
        data = ':SOUR:DEL %s'%float(delay)
        #print data
        return self.write(data)
        
    def setSweepRangingMode(self,mode):
        if mode not in ['BEST','AUTO','FIXED']:
            raise Exception('not valid sweeping range mode %s'%mode)
        return self.write(':SOUR:SWE:RANG %s'%mode)
    
    def setVoltSourceMode(self,mode):
        if mode not in ['FIXED','MIXED','SWEEP']:
            raise Exception( 'VoltSourceMode not valid: %s'%mode)
        return self.write(':SOUR:VOLT:MODE %s'%mode)

    def setSweepSpacingType(self,type):
        if type not in ['LIN','LOG']:
            raise Exception('Sweep Spacing Type not valid %s'%type)
        return self.write(':SOUR:SWE:SPAC %s'%type)
        
    
    def setSenseFunction(self,function):
        #todo: check if function ok..
        return self.write(':SENSE:FUNC \"%s\"'%function)
    
    def setSenseResistanceRange(self,resRange):
        #:SENSe:RESistance:RANGe
        if  self.is_float(resRange):
            
            #todo check if value is valid
            return self.write(':SENSe:RESistance:RANGe %s'%resRange)
        else:
            print 'resistance is not in valid Range %s'%resRange
            return False
        pass
    
    def setSenseResistanceMode(self,mode):
        #:SENSe:RESistance:MODE <name>
        if mode in ['MAN','AUTO','MANUAL']:
            return self.write(':SENSE:RESISTANCE:MODE %s'%mode)
        else:
            print 'Sense Resistance mode is not valid: %s'%mode
            return False
        pass
    
    def setSenseResistanceOffsetCompensated(self,state):
        #:SENSe:RESistance:OCOMpensated <state>
        if not self.is_number(state):
            if state in ['True','TRUE','1','ON','On']:
                state = True
            elif ['False','FALSE','0','OFF','Off']:
                state= False
            else :
                print 'Four Wire Measurement not valid state: %s'%state
                return False
        if state:
            return self.write(':SENSE:RESISTANCE:OCOMPENSATED ON')
        else:
            return self.write(':SENSE:RESISTANCE:OCOMPENSATED OFF')
        
    def setSenseVoltageProtection(self,protVolt):
        #:SENSe:VOLTage:PROTection
        if self.is_float(protVolt):
            if self.validVoltage(protVolt):
                return self.write(':SENSE:VOLT:PROTECTION %s'%protVolt)
            else:
                print 'Protection Voltage not in valid area: %s'%protVolt
                return False
        else:
            print 'Protection Voltage no a Float: %s'%protVolt
        pass
    
    def setSourceFunction(self,function):
        if function in ['VOLT','CURR','VOLTAGE','CURRENT']:
            return self.write(':SOURCE:FUNC %s'%function)
        else:
            print 'try to set not valid source Function: %s'%function
            return False
        pass
    
    def setFourWireMeasurement(self,state=True):
        #:SYSTem:RSENse
        if not self.is_number(state):
            if state in ['True','False','TRUE','FALSE']:
                state = True
            else :
                print 'Four Wire Measurement not valid state: %s'%state
                return False
        if state:
            return self.write(':SYSTEM:RSENSE ON')
        else:
            return self.write('SYSTEM:RSENSE OFF')
        pass
    
    def getTriggerCount(self):
        data = self.getAnswerForQuery(':TRIG:COUN?')
        if data=='':
            return -1
        print 'receivedData: %s'%data
        nTrig = int(data)
        print 'TriggerCOunter: %s'%nTrig
        if nTrig>0 and nTrig <=2500:
            return nTrig
        else:
            return -1
            
    def getSweepPoints(self):
        print 'getSweepPoints'
        data = self.getAnswerForQuery(':SOUR:SWE:POIN?')
        print 'receivedData %s'%data
        if data =='':
            return -1
        nSweepPoints = int(data)
        print 'Sweep Points: %s'%nSweepPoints
        if nSweepPoints>0 and nSweepPoints <=2500:
            return nSweepPoints
        else:
            return -1
    
        #see page 18-52 in Keithley manual: 24bit-Status word
        #Bit 3 == 0x08 Compliance equivalent to Current Protection
    def isTriped(self,statusword):
        bit = 0x08
        if int(statusword)&bit == bit:
            return True
        return False
    
    
    def getAnswerForQuery(self,data,minlength =1):
        print 'getAnswer for query: %s'%data
        self.write(data)
        time.sleep(self.readSleepTime)
        data = self.read(minlength)
        print 'length is %s'%len(data)
        return self.clearString(data)
    
    def  validVoltage(self,value): #TODO Write function which 'knows' if the voltage is possible
        return True
    
    def validCurrent(self,current): #TODO
        return True
    
    def clearString(self,data):
        data = data.translate(None,self.removeCharacters)
        data = data.translate(maketrans(',',' '))
        return data.strip()
    
    def convertData(self,timestamp,data):
        if type(data)==str:
            newData = data.split(' ')
        elif type(data)==list:
            newData=data
        else:
            raise Exception('convertDAta: unvalid type!')
        if len(newData)%5 != 0:
            raise Exception('Something is wrong with the string, length=%s  \'%s\''%(len(newData),data))
            return -1
        if len(newData)>5:
            retVal = self.convertData(timestamp,newData[:5])
            retVal = self.convertData(timestamp,newData[5:])
        measurment = [float(x) for x in newData]
        measurment.insert(0,timestamp)
        self.measurments.append(measurment)
        self.lastVoltage = measurment[0]
        tripped = self.isTriped(measurment[5])
        print '%s:\tMeasured at %s V: %s A, %s, %s, %s \t=> new Length of Queue: %s'%(measurment[0],measurment[1],measurment[2],measurment[3],measurment[4],tripped,len(self.measurments))
        if tripped:
            return False
        else:
            return True
        
    def readSweepOutput(self,nTrig,firstCall):
        time.sleep(1.0)
        data =''
        if firstCall:
            data = self.read(69)
        else:
            data= self.read(70)
        timestamp = time.time()
        isLastOfSweep= (data.find('\r')<0)
        data = self.clearString(data)
        tripped = not self.convertData(timestamp,data)
        retVal =-3
        if tripped:
            retVal = 0
            print 'Keithley is Tripped'
            
        #print '%s, %s: %s'%(nTrig,len(data),data)
        if retVal==-3:
            print 'RetVal %s'%retVal
            if  nTrig >=0:
                if isLastOfSweep:
                    retVal = self.readSweepOutput(nTrig,False)
                else:
                    #print 'found last Sweep Point: EXIT'
                    retVal =1 
                nTrig -= 1
            else:
                retVal= -1
        
        print 'readSweepOutput RetVal: %s'%retVal
        return retVal
    
    def initFourWireResistensMeasurement(self):
        #self.reset()
        self.setSenseFunction('\'RESISTANCE\'')
        self.setConcurrentMeasurments()
        self.setSenseResistanceMode('AUTO')
        self.setSenseResistanceRange(2e3)
        self.setSenseResistanceOffsetCompensated('ON')
        self.setRearOutput(False)
        #self.setSenseVoltageProtection(protVolt)
        #self.setCurrentProtection(value)
        self.setSourceFunction('CURR')
        self.setFourWireMeasurement(True)
        self.setOutput(True)
#        self.setFO
        #:FORM:ELEM RES #READ RESISTANCE
        #:OUTPut <state>
        #:READ?
    def doLinearSweep(self,startValue,stopValue,stepValue,nSweeps,delay):
        print self.clearErrorQueue()
        print self.clearBuffer()
        print self.setMeasurementDelay(delay)
        print self.setSweepRangingMode('BEST')
        print self.setSweepSpacingType('LIN')
        print self.setVoltSourceMode('SWEEP')
        print self.setVoltageSweepStartValue(startValue)
        print self.setVoltageSweepStopValue(stopValue)
        
        if (stopValue-startValue)/stepValue <0:
            stepValue *= -1
        print self.setVoltageSweepStepValue(stepValue)
        print stopValue
        print startValue
        print stepValue
        nTrig = int(stopValue-startValue)
        print 'Delta: %s'%nTrig
        nTrig = nTrig/stepValue
        print nTrig
        nTrig +=1
        print nTrig
        nTrig = int(nTrig)
        print nTrig
        nTrig *= nSweeps
        nTrig = int(nTrig)
        print nTrig
        print self.setTriggerCounter(nTrig)
        print self.setOutput(True)
        self.write(':READ?')
        retVal =  self.readSweepOutput(nTrig,True)
        print 'doLinearSweep retVal %s'%retVal
        return retVal
                            
    def initKeithley(self):
        self.setOutput(False)
        self.reset()
        self.clearBuffer()
        self.setOutput(False)
        self.setRearOutput()
        self.setFixedVoltMode()
        self.setStandardOutputForm()
        self.setConcurrentMeasurments(True)
        self.setDigitalFilterType('REP')
        self.setAverageFiltering(True)
        self.setAverageFilterCount(3)
        self.setCurrentProtection(100e-6)
        self.setCurrentMeasurmentSpeed(10)
        self.setImmidiateVoltage(-150)
        self.clearErrorQueue()
        self.setComplianceAbortLevel('LATE')
        
        
    def is_number(self,s):
        try:
            int(s)
            return True
        except ValueError:
            return False

    def is_float(self,s):
        try:
            float(s)
            return True
        except ValueError:
            return False
        
