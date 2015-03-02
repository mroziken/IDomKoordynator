#!/usr/bin/python
# -*- coding: utf-8 -*-
import logging.handlers
import sqlite3
from time import sleep
from datetime import datetime
import sys
from mxmutls import str2date
from mxmutls import MyLogger
from mxmutls import MYDB

def processPending():
    rowsToProcess = selectPending()
    rowToProcess = None
    result = False
    if rowsToProcess:
        print 'processPending: found pending'
        for rowToProcess in rowsToProcess:
            print rowToProcess
            ts=rowToProcess[0]
            addr=rowToProcess[1]
            rawMsg=rowToProcess[2]
            (msgType,pin,val,msgTs)=parseMsg(rawMsg)
            if (msgType=='err'):
                result = handleERR(ts,msgType,addr,rawMsg)
            elif (msgType=='info'):
                result = handleMSG(ts,msgType,addr,rawMsg)
            elif (msgType=='rep'):
                msgTs=str2date(msgTs)
                result = handleREP(ts,msgType,addr,pin,val,msgTs)
            else:
                result = False
            if result:
                procStat='C'
            else:
                procStat='E'
            updateStatus(ts,addr,procStat)

def selectPending():
    query = '''select ts,dev,msg from logserial where stat is null'''
    params = ''
    return mydb.executeSelect(query, params)


def parseMsg(msg):
    print 'In parseMsg', (msg)
    msgType=None # rep -for replay, info - for pushed messages, err - for error messages
    pin=None
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

def handleERR(ts,msgtype,dev,msg):
    print 'In handleERR',ts, msgtype, dev, msg
    return True

def handleMSG(ts,msgtype, dev,msg):
    print 'In handleMSG', (ts, msgtype, dev, msg)
    return True

def handleREP(ts,msgtype, address,pin,val,msgTs):
    print 'In handleRep',(ts,msgtype, address,pin,val,msgTs)
    result = False
    endpoint=getEndpoint(address)
    if (pin[0]=='A' or pin[0] == 'D'):
        if(pin[1].isdigit() and val.isnumeric()):
            if(setPINvalue(endpoint,pin,val)):
                result = updateCmdStatus(msgTs,'S')
        else:
            print 'Error: incorrect values'
    else:
                if(setPINvalue(endpoint,'V',None,pin,val)):
                    result = updateCmdStatus(msgTs,'S')
    return result

def getEndpoint(dev):
    print 'In getEndpoint',(dev)
    query = '''select endpoint from endpointaddr where address=?'''
    params = (dev,)
    return mydb.executeSelectOne(query, params)

def updateCmdStatus(ts,stat):
    print 'In updateCmdStatus',(ts,stat)
    #####################################
    #Possible statuses of commands are: #
    #    P - Pending for execution      #
    #    R - Waiting replay             #
    #    S - Successfully completed     #
    #    E - Error                      #
    #####################################
    query = '''update cmdjrnl set stat='%s', statts='%s' where ts='%s' ''' % (stat,datetime.now(),ts)
    print query
    return mydb.executeUpdate(query)


def setPINvalue(endpoint,pin,stat=None,vname=None,vval=None):
    print 'In setPINvalue',(endpoint,pin,stat,vname,vval)
    pinType=pin[0]
    pinNumber=pin[1:]
    return updateMenu(endpoint,pinType,pinNumber,stat,vname,vval)

def updateMenu(endpoint,pintype,pinnumber,state,vname,vval):
    print 'In updateMenu',(endpoint,pintype,pinnumber,state,vname,vval)
    if (vname and vval):
        query = '''update menu set  vval='%s' where endpoint='%s' and pintype='%s' and vname='%s' ''' % (vval,endpoint,pintype,vname)
        params = ''
    else:
        query = '''update menu set state=%s where endpoint = '%s' and pintype='%s' and pinnumber=%s''' % (state,endpoint,pintype,pinnumber)
        params = ''
    print query
    return mydb.executeUpdate(query,params)


def updateStatus(ts,addr,procStat):
    print 'In updateStatus',(ts,addr,procStat)
    query = '''update logserial set stat=? where ts=? and  dev=?'''
    params = (procStat,ts,addr)
    return mydb.executeUpdate(query,params)


DB = 'dev.db'
mydb = MYDB(DB)

LOG_FILENAME = "log/logserialParser.log"
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

# Replace stdout with logging to file at INFO level
sys.stdout = MyLogger(logger, logging.INFO)
# Replace stderr with logging to file at ERROR level
sys.stderr = MyLogger(logger, logging.ERROR)


while True:
    processPending()    
    sleep(0.5)

