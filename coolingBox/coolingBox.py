import math
import time

class coolingBox():
    UNKNOWN = -1
    FLUSHING = 0
    COOLING = 1
    HEATING = 2
    FINAL_HEATING = 3
    

    def __init__(self):
        self.setpoint = -9999
        self.maxHumidity = 40
        self.deltaT_Max = 1.5
        self.temperature_safty_margin = 1
        self.checkHumidity = True
        self.cycleLow = -10
        self.cycleHigh = +10
        self.cycles = -1
        self.cycleAdditionalTemp = 2
        self.doCycle = False
        self.RH_start_cooling = 10.0
        self.RH_maximum = 40.00
        self.status = self.UNKNOWN
        pass
        
    def is_cooling(self):
        return self.status == self.COOLING
    def is_heating(self):
        return self.status == self.HEATING
    def is_flushing(self):
        return self.status == self.FLUSHING
    def is_unkown(self):
        return self.status == self.UNKNOWN
    def is_final_heating(self):
        return self.status == self.FINAL_HEATING

    def start_controlling(self):
        pass

    def set_setpoint(self,temp):
        self.setpoint = temp

    def get_temperature(self):
        return 9999

    def get_relative_humidity(self):
        return 100


    def do_cycle(self,nCycles,**kwargs):
        tempLow=kwargs.get('tempLow',self.cycleLow)
        tempHigh = kwargs.get('tempHigh',self.cycleHigh)
        print 'Do %s Temperature cycles between %s and %s deg C'%(nCycles,tempLow,tempHigh)
        self.doCycle = True
        self.cycles = nCycles
        self.cycleLow = tempLow
        self.cycleHigh = tempHigh
        self.set_setpoint(tempHigh+self.cycleAdditionalTemp)
        time.sleep(1.0)

        return False


    def is_dry(self):
        #print 'isDry?'
        dewPoint = self.get_dew_point()
        relHum =  self.get_relative_humidity()
        retVal =  self.setpoint - dewPoint > self.temperature_safty_margin
        retVal = retVal or relHum < self.RH_start_cooling
        if not self.is_unkown() and not self.is_flushing():
            retVal = retVal or relHum < self.RH_maximum
        #print '\tdewPoint: %s\t\t--> %s'%(dewPoint,retVal)
        if self.setpoint == -9999:
            return True
        if self.checkHumidity == False:
            return True
        return retVal

    def is_stable(self):
        return False
        pass

    def stablize():
        pass

    def check_cycles():
        pass

    def final_heating():
        pass

    def get_dew_point(self):
        temp = self.get_temperature()
        hum = self.get_relative_humidity()
        return self.calculate_dew_point(temp,hum)
#
#@brief function to calculate dew point out of temperature and relative humidity
#Formula from http://ag.arizona.edu/azmet/dewpoint.html
#B = (ln(RH / 100) + ((17.27 * T) / (237.3 + T))) / 17.27
#D = (237.3 * B) / (1 - B)
#
#where:
#            T = Air Temperature (Dry Bulb) in Centigrade (C) degrees
#            RH = Relative Humidity in percent (%)
#            B = intermediate value (no units)
#            D = Dewpoint in Centigrade (C) degrees
#@param T Air Temperature in deg C
#@param RH Relative Humidity in percent
#@retVal Dew Point in Deg C
#
    def calculate_dew_point(self,T,RH):
        B =(math.log(float(RH) / 100.) + ((17.27 * float(T)) / (237.3 +float( T)))) / 17.27;
        D = (237.3 * B) / (1 - B);
        return D;
        
