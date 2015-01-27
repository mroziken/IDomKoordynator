#!/usr/bin/python
# -*- coding: utf-8 -*-
from xbee import ZigBee
import serial
import logging.handlers
import sqlite3
import sys
from time import sleep
from datetime import  datetime

# Make a class we can use to capture stdout and sterr in the log
class MyLogger(object):
	def __init__(self, logger, level):
		"""Needs a logger and a logger level."""
		self.logger = logger
		self.level = level
 
	def write(self, message):
		# Only log if there is a message (not just a new line)
		if message.rstrip() != "":
			self.logger.log(self.level, message.rstrip())
 
# Replace stdout with logging to file at INFO level
#sys.stdout = MyLogger(logger, logging.INFO)
# Replace stderr with logging to file at ERROR level
#sys.stderr = MyLogger(logger, logging.ERROR)

	
def readSerial(data):
	print 'Reading from serial '
	print data
	
def err(msg):
	print msg
	return 1

def selectPendingCmd():
	db = None
	rows = None
	try:
		db = sqlite3.connect(DB)
		cur=db.cursor()
		cur.execute('''select ts,address,cmd,dev,addr from cmdjrnl where stat='P' order by ts asc''')
		rows=cur.fetchall()
	except sqlite3.Error, e:
		print "error %s:" % e.args[0]
	finally:
		if db:
			db.close()
		return rows

def updateCmdStatus(ts,dev,cmd,stat):
	print 'In updateCmdStatus'
	###################################
	#Posible statuses of commands are:#
	#	P - Pendig for execution  #
	#	S - Sucsssrully completed #
	#	E - Error                 #
	###################################
	db = None
	result=True
	try:
		db = sqlite3.connect(DB)
		cur=db.cursor()
		cur.execute('''update cmdjrnl set stat=?, statts=? where ts=? and dev=?''',(stat,datetime.now(),ts,dev))
		db.commit()
	except sqlite3.Error, e:
		print "Error: %s" % e.args[0]
		result=False
	except Exception, e:
		print repr(e)
		result=False
	finally:
		if db:
			db.close()
		return result

def updateLogSerial(msgtype,dev,msg):
	print 'In updateLogSerial'
	db = None
	result=True
	try:
		db = sqlite3.connect(DB)
		cur=db.cursor()
		sqlstmt='''INSERT INTO logserial (TS,MSGTYPE,DEV,MSG) VALUES('%s','%s','%s','%s')''' % (datetime.now(),msgtype,dev,msg)
		print sqlstmt
		cur.execute(sqlstmt)
		db.commit()
	except  sqlite3.Error, e:
		print "Error: %s" % e.args[0]
		result=False
	except Exception, e:
		print repr(e)
		result=False
	finally:
		if db:
			db.close()
		return result

def xbeeSend(ts,address,addr,cmd):
	#RETRIES=3
	#MSGSTAT=False
	#DEST_ADDR_LONG='\x00\x13\xA2\x00\x40\xB1\x91\x62'
	DEST_ADDR_LONG=address
	DEST_ADDR=addr
	#cmdRow='2014102023310212345\x1800'
	cmdRow=ts+cmd
	print ('''xbee command: 'tx', dest_addr_long=%s, dest_addr=%s, data=%s ''' % (DEST_ADDR_LONG.encode("hex"),DEST_ADDR.encode("hex"),cmdRow.encode("hex"),))
	xbee.send('tx',dest_addr_long=DEST_ADDR_LONG, dest_addr=DEST_ADDR, data=cmdRow)
	#
	#for tries in range(0,RETRIES):
	#	print ("Loop: "+str(tries))
	#	try:
	#		response = xbee.wait_read_frame()
	#		if (response['deliver_status'] == '\x00'):
	#			print("Message delivered")
	#			MSGSTAT=True
	#			break
	#		else:
	#			print("Message not delivered")
	#	except Exception:
	#		print sys.exc_info()
	#	
	#if (MSGSTAT):
	#	return True
	#else:
	#	return False
	return True
		

def parseSerial(line):
	if (len(line) >= 7):
		type=line[:3]
		dev=line[3:7]
		msg=line[7:]
		updResult=updateLogSerial(type, dev, msg)
	else:
		updaResult=updateLogSerial('JNK','',line)

def convert2hex(str,step=2):
	ret=''
	if (step<=0):
		print "Step must be >0"
	elif (len(str)%step>0):
		print "Length of str not multiple of step"
	else:
		for i in range (0, len(str), step):
			if (step==1):
				ret+=('0'+str[i:i+step]).decode("hex")
			else:
				ret+=str[i:i+step].decode("hex")
	return ret

def date2str(date):
	yyyy=date[0:4]
	mm=date[5:7]
	dd=date[8:10]
	hh=date[11:13]
	mi=date[14:16]
	ss=date[17:19]
	ssssss=date[20:26]
	return yyyy+mm+dd+hh+mi+ss+ssssss
	

ser = serial.Serial("/dev/ttyUSB1", baudrate=38400)
#xbee = ZigBee(ser,escaped=True)

DB = 'dev.db'

LOG_FILENAME = "/tmp/xbeelistener.log"
LOG_LEVEL = logging.INFO # Could be e.g. "DEBUG" or "WARNING"

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

xbee = ZigBee(ser, escaped = True, callback=readSerial)

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
				addr=convert2hex(cmdRow[4])
				#print "ts:"+ts+" address:"+address.decode("hex")+" addr"+addr.decode("hex")+" cmd"+cmd
				if (xbeeSend(convert2hex(date2str(ts),1),address,addr,cmd)):
					print 'Write to serial successful and waiting for replay'
					updResult=updateCmdStatus(ts,dev,cmd,'R')
				else:
					print 'Write to serial unsucessful'
					updResult=updateCmdStatus(ts,dev,cmd,'E')
					print 'Update status result: %s' % updResult
		sleep(0.5)
	except KeyboardInterrupt:
		break

xbee.halt()
ser.close()
