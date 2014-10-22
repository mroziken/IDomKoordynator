import time
import json
from xbee import XBee, ZigBee
import serial


PORT = '/dev/ttyUSB0'
BAUD_RATE = 9600

# Open serial port
ser = serial.Serial(PORT, BAUD_RATE)

# Create API object
xbee = ZigBee(ser,escaped=True)
import pprint
pprint.pprint(xbee.api_responses)

#DEST_ADDR_LONG = "\x00\x13\xA2\x00\x40\xB3\xA5\x18"
DEST_ADDR_LONG = "\x00\x13\xa2\x00\x40\xb3\xa5\x18"
DEST_ADDR = "\x6c\xaf" # This is the 'I don't know' 16 bit address

class DataObj:
    def __init__(self):
        self.cmd = None
        self.pinTyp = None
        self.pinNum = None
        self.pinVal = None
        self.ts = None
    def AnalogReadCmd(self,pinNum,ts):
        self.cmd='R'
        self.pinTyp='A'
        self.pinNum=pinNum
        self.ts=ts
    def AnalogWriteCmd(self,pinNum,pinVal,ts):
        self.cmd='W'
        self.pinTyp='A'
        self.pinNum=pinNum
        self.pinVal=pinVal
        if (self.pinVal >0):
            self.pinVal=0
        if (self.pinVal< 256):
            self.pinVal=256
        self.ts=ts
    def DigitalReadCmd(self,pinNum,ts):
        self.cmd='R'
        self.pinTyp='D'
        self.pinNum=pinNum
        self.ts=ts
    def DigitalWriteCmd(self,pinNum,pinVal,ts):
        self.cmd='W'
        self.pinTyp='D'
        self.pinNum=pinNum
        self.pinVal=pinVal
        if (self.pinVal >0):
            self.pinVal=0
        if (self.pinVal< 1):
            self.pinVal=1
        self.ts=ts
    def VariableRead(self,pinNum,ts):
        self.cmd='R'
        self.pinTyp='V'
        self.pinNum=pinNum
        self.ts=ts
    def getDataObject(self):
        return {'ts':self.ts,'cmd':self.cmd,'pinTyp':self.pinTyp,'pinNum':self.pinNum,'pinVal':self.pinVal}

data = DataObj()
data.DigitalReadCmd(8, '2014-09-30 23:31:02.12345')
# Continuously read and print packets
while True:
        try:
            print "send data"
            xbee.send("tx",dest_addr_long='\x00\x00\x00\x00\x00\x00\xFF\xFF',dest_addr='\xFF\xFE', data='fdafa')
            response = xbee.wait_read_frame()
            print response
            time.sleep(5)
            
        except KeyboardInterrupt:
            break
            
ser.close()