#!/usr/bin/python
# -*- coding: utf-8 -*-
from xbee import ZigBee
import serial
import logging.handlers
import sys
import json
from time import sleep
from datetime import  datetime
from mxmutls import MYDB
from mxmutls import MyLogger
from mxmutls import convert2hex
from mxmutls import date2str
from mxmutls import HexToByte
from mxmutls import ByteToHex

def readSerial(data):
	print 'Reading from serial '
	print data
	mydb1=MYDB(DB)
	if (data['id']=='tx_status'):
		if (data['deliver_status'] == '\x00'):
			updateCmdStatusFrameId('D',data['frame_id'],mydb1)
		else:
			updateCmdStatusFrameId('D',data['frame_id'],mydb1)
	elif(data['id']=='rx'): 
		insertLogserial(mydb1,data['rf_data'],ByteToHex(data['source_addr_long']))

		
def xbeeSeq(seq):
	seq=seq+1
	if (seq>=255):
		seq=1
	return seq
	

def selectPendingCmd():
	query = '''select ts,address,cmd,dev,addr,pin,val from cmdjrnl where stat=? order by ts asc'''
	params = ('P',)
	return mydb.executeSelect(query, params)

def insertLogserial(mydb1,rfData,dev):
	query = '''insert into logserial(ts,dev,msg) values (?,?,?)'''
	params = (datetime.now(),dev,rfData)
	return mydb1.executeInsert(query,params)


def updateCmdStatus(ts,dev,cmd,stat,frameId):
	print 'In updateCmdStatus'
	####################################
	#Possible statuses of commands are:#
	#	P - Pending for execution      #
	#   T - Transmitted                #
	#   D - Delivered	               #
	#   N - Not Delivered              #
	#	S - Successfully completed     #
	#	E - Error                      #
	#   O - Obsoleted                  #
	####################################
	query = '''update cmdjrnl set stat=?, statts=?, frameId=? where ts=? and dev=?'''
	params = (stat,datetime.now(),frameId,ts,dev)
	print (query, params)
	return mydb.executeUpdate(query, params)

def updateCmdStatusFrameId(stat,frameId,mydb1):
	print 'In updateCmdStatusFrameId'
	####################################
	#Possible statuses of commands are:#
	#	P - Pending for execution      #
	#   T - Transmitted                #
	#   D - Delivered	               #
	#   N - Not Delivered              #
	#	S - Successfully completed     #
	#	E - Error                      #
	#   O - Obsoleted                  #
	####################################
	query = '''update cmdjrnl set stat=?, statts=? where frameId=?'''
	params = (stat,datetime.now(),frameId)
	print (query, params)
	return mydb1.executeUpdate(query, params)
	

def updateLogSerial(msgtype,dev,msg):
	print 'In updateLogSerial'
	query = '''INSERT INTO logserial (TS,MSGTYPE,DEV,MSG) VALUES('%s','%s','%s','%s')''' % (datetime.now(),msgtype,dev,msg)
	params = ''
	return mydb.executeInsert(query,params)


def xbeeSend(ts,address,addr,pincmd,pinnumber,pinval):
	global SEQ
	#cmdRow=ts+cmd	
	#cmdRow='''{"cmd":"RD","time":1351824120,"p1":7,"p2":0}'''
	cmdRow=jsonCmdString(pincmd,pinnumber,pinval,ts)
	print ('''xbee command: 'tx', dest_addr_long=%s, dest_addr=%s, data=%s, frame_id=%s''' % (address.encode("hex"),addr.encode("hex"),cmdRow.encode("hex"),str(hex(SEQ)),))
	xbee.send('tx',dest_addr_long=address, dest_addr=addr, data=cmdRow, frame_id=HexToByte(str(hex(SEQ)[2:])))
	
def jsonCmdString(pincmd,pinnumber,pinval,time):
	x={}
	if (pincmd.equal('WD') or pincmd.equal('WA') or pincmd.equal('RD') or pincmd=('RA')):
		x={'cmd':pincmd,'p1':int(pinnumber),'p2':int(pinval),'tm':time}
	else:
		x={'cmd':pincmd,'p1':pinnumber,'p2':pinval,'tm':time}
	return json.dump(x)
			

#def parseSerial(line):
#	if (len(line) >= 7):
#		type=line[:3]
#		dev=line[3:7]
#		msg=line[7:]
#		updResult=updateLogSerial(type, dev, msg)
#	else:
#		updaResult=updateLogSerial('JNK','',line)


BOUDRATE=9600
SERIAL="/dev/ttyAMA0"
DB = 'dev.db'
LOG_FILENAME = "log/xbeelistener.log"
LOG_LEVEL = logging.INFO # Could be e.g. "DEBUG" or "WARNING"
SEQ=1

		
 
logger = logging.getLogger(__name__)
# Set the log level to LOG_LEVEL
logger.setLevel(LOG_LEVEL)
# Make a handler that writes to a file, making a new file at midnight and keeping 3 backups
handler = logging.handlers.TimedRotatingFileHandler(LOG_FILENAME, when="midnight", backupCount=3)
# Format each log message like this
formatter = logging.Formatter('%(asctime)s %(levelname)-8s %(message)s')
# Attach the formatter to the handler
handler.setFormatter(formatter)
# Attach the handler to the logger
logger.addHandler(handler)

# Replace stdout with logging to file at INFO level
sys.stdout = MyLogger(logger, logging.INFO)
# Replace stderr with logging to file at ERROR level
sys.stderr = MyLogger(logger, logging.ERROR)

ser = serial.Serial(SERIAL, baudrate=BOUDRATE)
xbee = ZigBee(ser, escaped = True, callback=readSerial)
mydb=MYDB(DB)

while True:
	try:
		lines = None
		cmdRows = None
		cmdRow = None
		
		#Fetch unprocessed commands
		cmdRows=selectPendingCmd()
		if (cmdRows):
			for cmdRow in cmdRows:
				ts=cmdRow[0]
				address=convert2hex(cmdRow[1])
				cmd=convert2hex(cmdRow[2])
				dev=cmdRow[3]
				pin=cmdRow[4]
				val=cmdRow[5]
				addr=convert2hex(cmdRow[4])
				xbeeSend(convert2hex(date2str(ts),1),address,addr,cmd,pin,val)
				updResult=updateCmdStatus(ts,dev,cmd,'T',HexToByte(str(hex(SEQ)[2:])))
				SEQ=xbeeSeq(SEQ)
		sleep(0.5)


	except KeyboardInterrupt:
		xbee.halt()
		ser.close()
		break

xbee.halt()
ser.close()
