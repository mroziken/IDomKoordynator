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
sys.stdout = MyLogger(logger, logging.INFO)
# Replace stderr with logging to file at ERROR level
sys.stderr = MyLogger(logger, logging.ERROR)

	
def readSerial():
	print 'Reading from serial '
	try:
		response = xbee.wait_read_frame(0.1)
		print response
	except:
		print "TimeoutException"
	
def err(msg):
	print msg
	return 1

def selectPendingCmd():
	db = None
	rows = None
	try:
		db = sqlite3.connect(DB)
		cur=db.cursor()
		cur.execute('''select ts,dev,cmd from cmdjrnl where stat='P' order by ts asc''')
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
		cur.execute('''update cmdjrnl set stat=?, statts=? where ts=? and dev=? and cmd=?''',(stat,datetime.now(),ts,dev,cmd))
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

def xbeeSend(cmd):
	RETRIES=3
	MSGSTAT=False
	DEST_ADDR_LONG='\x00\x13\xA2\x00\x40\xB1\x91\x62'
	DEST_ADDR='\x40\x2E'
	cmdRow='2014102023310212345\x17\x01'
	print ('''xbee command: 'tx', dest_addr_long=%s, dest_addr=%s, data=%s ''' % (DEST_ADDR_LONG.encode("hex"),DEST_ADDR.encode("hex"),cmdRow.encode("hex"),))
	xbee.send('tx',dest_addr_long=DEST_ADDR_LONG, dest_addr=DEST_ADDR, data=cmdRow)
	for tries in range(0,RETRIES):
		print ("Loop: "+str(tries))
		try:
			response = xbee.wait_read_frame(0.5)
			print response
			if (response['deliver_status'] == '\x00'):
				print("Message delivered")
				MSGSTAT=True
				break
			else:
				print("Message not delivered")
		except:
			print "TimeoutException"
		
	if (MSGSTAT):
		return True
	else:
		return False
		

def parseSerial(line):
	if (len(line) >= 7):
		type=line[:3]
		dev=line[3:7]
		msg=line[7:]
		updResult=updateLogSerial(type, dev, msg)
	else:
		updaResult=updateLogSerial('JNK','',line)


ser = serial.Serial("/dev/ttyUSB0", baudrate=38400, timeout=1)
xbee = ZigBee(ser,escaped=True)

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

while True:
	lines = None
	cmdRows = None
	cmdRow = None
	
	#Reading serial
	readSerial()

	#Fetch unprocessed commands
	cmdRows=selectPendingCmd()
	if (cmdRows):
		for cmdRow in cmdRows:
			ts=cmdRow[0]
			dev=cmdRow[1]
			cmd=cmdRow[2]
			if (xbeeSend(cmd)):
				print 'Write to serial successful and waiting for replay'
				updResult=updateCmdStatus(ts,dev,cmd,'R')
			else:
				print 'Write to serial unsucessful'
				updResult=updateCmdStatus(ts,dev,cmd,'E')
			print 'Update status result: %s' % updResult
	else:
		print 'No rows selected'
	sleep(0.5)


