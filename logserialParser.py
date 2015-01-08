#!/usr/bin/python
# -*- coding: utf-8 -*-
import logging.handlers
import sqlite3
from time import sleep
from datetime import datetime
#Ala ma kota

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
		cur.execute('''select ts,devtype,dev,msg from logserial where stat is null ''')
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
            devType=rowToProcess[1]
            addr=rowToProcess[2]
            rawMsg=rowToProcess[3]
            (msgType,pin,val,msgTs)=parseMsg(rawMsg)
            if (msgType=='err'):
                result = handleERR(ts,msgType,addr,rawMsg)
            elif (msgType=='info'):
                result = handleMSG(ts,msgType,addr,rawMsg)
            elif (msgType=='rep'):
                msgTs=StrToDate(msgTs)
                result = handleREP(ts,msgType,addr,pin,val,msgTs)
            else:
                result = False
            if result:
                procStat='C'
            else:
                procStat='E'
            updateStatus(ts,devType,addr,procStat)

def StrToDate(Str):
    yyyy=Str[0:4]
    mm=Str[4:6]
    dd=Str[6:8]
    HH=Str[8:10]
    MI=Str[10:12]
    SS=Str[12:14]
    SSSSS=Str[14:20]
    return yyyy+'-'+mm+'-'+dd+' '+HH+':'+MI+':'+SS+'.'+SSSSS

def parseMsg(msg):
    print 'In parseMsg'
    msgType=None # rep -for replay, info - for pushed messages, err - for error messages
    pinType=None
    pinNumber=None
    val=None
    ts=None
    (pin,val,ts) = msg.split('=')
    if (pin=='ER'):
        msgType='err'
        pin=None
    else:
        if (ts==''):
            msgType='info'
            ts=None
        else:
            msgType='rep'
    return msgType,pin,val,ts

def updateCmdStatus(ts,stat):
    print 'In updateCmdStatus'
    ###################################
    #Posible statuses of commands are:#
    #    P - Pending for execution     #
    #   R - Waiting replay            #
    #    S - Sucsssrully completed     #
    #    E - Error                     #
    ###################################
    db = None
    result=True
    try:
        db = sqlite3.connect(DB)
        cur=db.cursor()
        print ('''update cmdjrnl set stat=%s, statts=%s where ts=%s''',(stat,datetime.now(),ts,))
        cur.execute('''update cmdjrnl set stat=?, statts=? where ts=?''',(stat,datetime.now(),ts,))
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

def handleERR(ts,msgtype,dev,msg):
	print ts, msgtype, dev, msg
	return True

def handleMSG(ts,msgtype, dev,msg):
	print ts, msgtype, dev, msg
	return True

def handleREP(ts,msgtype, dev,pin,val,msgTs):
    print 'In handleRep'
    result = False
    if (pin[0]=='A' or pin[0] == 'D'):
        if(setPINvalue(dev,pin,val)):
            result = updateCmdStatus(msgTs,'S')
    else:
        if(setPINvalue(dev,'V',None,pin,val)):
            result = updateCmdStatus(msgTs,'S')
    return result


def updateMenu(endpoint,pintype,pinnumber,state,vname,vval):
    print 'In updateMenu'
    db = None
    result = True
    try:
        db = sqlite3.connect(DB)
        cur = db.cursor()
        endpoint = endpoint+'%' # To jest do poprawy. Należy sprawdzić dlaczego adress nie jest kompletny
        if (vname and vval):
            print ('''update menu set state=%s,vval=%s where endpoint=%s and pintype=%s and pinnumber=%s and vname=%s''', (state,vval,endpoint,pintype,pinnumber,vname))
            cur.execute('''update menu set state=?,vval=? where endpoint=? and pintype=? and pinnumber=? and vname=?''', (state,vval,endpoint,pintype,pinnumber,vname))
        else:
            print ('update menu set state=%s where endpoint in (select endpoint from endpointaddr where address like %s) and pintype=%s and pinnumber=%s' % (state,endpoint,pintype,pinnumber))
            cur.execute('''update menu set state=? where endpoint in (select endpoint from endpointaddr where address like ?) and pintype=? and pinnumber=?''', (state,endpoint,pintype,pinnumber)) 
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

def setPINvalue(endpoint,pin,stat=None,vname=None,vval=None):
    print 'In setPINvalue'
    pinType=pin[0]
    pinNumber=pin[1:]
    return updateMenu(endpoint,pinType,pinNumber,stat,vname,vval)


def updateStatus(ts,msgtype,dev,stat):
    db = None
    result = True
    try:
        db = sqlite3.connect(DB)
        cur = db.cursor()
        cur.execute('''update logserial set stat=? where ts=? and devtype=? and dev=?''',(stat,ts,msgtype,dev))
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

