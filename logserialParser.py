#!/usr/bin/python
# -*- coding: utf-8 -*-
import logging
import logging.handlers
import sqlite3
from time import sleep
from datetime import date, datetime

LOG_FILENAME = "logserialParser.log"
LOG_LEVEL = logging.INFO # Could be e.g. "DEBUG" or "WARNING"

DB = '/home/michal/workspace/iDomKoordynator/dev.db'

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


def selectPending():
	print 'In selectPending'
	db = None
	rows = None
	try:
		db = sqlite3.connect(DB)
		cur=db.cursor()
		cur.execute('''select ts,msgtype,dev,msg from logserial where stat is null ''')
		rows=cur.fetchall()
	except sqlite3.Error, e:
		print "error %s:" % e.args[0]
	finally:
		if db:
			db.close()
		return rows

def processPending():
	print 'In processPending'
	rowsToProcess = selectPending()
	rowToProcess = None
	result = False
	if rowsToProcess:
		print 'processPending: found pending'
		for rowToProcess in rowsToProcess:
			print rowToProcess
			ts=rowToProcess[0]
			msgtype=rowToProcess[1]
			dev=rowToProcess[2]
			msg=rowToProcess[3]
			
			if (msgtype=='err'):
				result = handleERR(ts,msgtype,dev,msg)
			elif (msgtype=='msg'):
				result = handleMSG(ts,msgtype,dev,msg)
			elif (msgtype=='rep'):
				result = handleREP(ts,msgtype,dev,msg)
			else:
				result = False
			if result:
				procStat='C'
			else:
				procStat='E'
			updateStatus(ts,msgtype,dev,procStat)
		

def handleERR(ts,msgtype,dev,msg):
	print ts, msgtype, dev, msg
	return True

def handleMSG(ts,msgtype, dev,msg):
	print ts, msgtype, dev, msg
	return True

def handleREP(ts,msgtype, dev,msg):
	cmd=msg[0-3]
	result = False
	if (cmd=='STRT'):
		print 'Device '+dev+'started at '+ts
	elif (cmd=='DITM'):
		result = setDITM(dev,msg)
	elif (cmd=='HWTM'):
		result = setWHTM(dev,msg)
	elif (cmd=='APIN'):
		pin=msg[4]
		value=int(msg[5:])
		result = setAPIN(dev,pin,value)
	elif (cmd=='DPIN'):
		pin=msg[4]
		value=int(msg[5:])
		result = setDPIN(dev,pin,value)
	else:
		print 'Unhandled command'
	return result


def setDPIN(endpoint,pin,stat):
	vname = None
	vval = None
	return updateEndpoints(endpoint,'D',pin,stat,vname,vval)

def setAPIN(endpoint,pin,stat):
	vname = None
	vval = None
	return updateEndpoints(endpoint,'A',pin,stat,vname,vval)

def setWHTM(endpoint,time):
	pin = None
	stat = None
	return updateEndpoints(endpoint,'V',3,stat,time)

def setDITM(endpoint,time):
        pin = None
        stat = None
        return updateEndpoints(endpoint,'V',4,stat,time)


def updateEndpoints(endpoint,pintype,pinnumber,state,vname,vval):
	db = None
	result = True
	try:
		db = sqlite3.connect(DB)
		cur = db.cursor()
		cur.execute('''update menu set endpoint=?,pintype=?,pinnumber=?, state=?, vname=?, vval=?''', (endpoint,pintype,pinnumber,state,vname,vval))
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

def updateStatus(ts,msgtype,dev,stat):
	db = None
	result = True
	try:
		db = sqlite3.connect(DB)
		cur = db.cursor()
		cur.execute('''update logserial set stat=? where ts=? and msgtype=? and dev=?''',(stat,ts,msgtype,dev))
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

while True:
	processPending()	
	sleep(0.5)

