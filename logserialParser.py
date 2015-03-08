#!/usr/bin/python
# -*- coding: utf-8 -*-
import logging.handlers
import sqlite3
from time import sleep
from datetime import datetime
import sys
import json
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
            cmdDict=convertToJsonStr(rowToProcess[2])
            msgType=cmdDict["tp"]
            msgTs=cmdDict["tm"]
            p1=cmdDict["p1"]
            v1=cmdDict["v1"]
            p2=cmdDict["p2"]
            v2=cmdDict["v2"]
            if (msgType=='err'):
                result = handleERR(ts,addr,p1)
            elif (msgType=='info'):
                result = handleMSG(ts,addr,p1,v1,p2,v2)
            elif (msgType=='rep'):
                msgTs=str2date(msgTs)
                result = handleREP(ts,addr,msgTs,p1,v1,p2,v2)
            else:
                result = False
            if result:
                procStat='C'
            else:
                procStat='E'
            updateStatus(ts,addr,procStat)

def convertToJsonStr(rawStr):
    rawJsonStr=rawStr.encode('ascii', 'ignore')
    if (rawJsonStr.find('\x00')>=0):
        print json.loads(rawJsonStr[0:rawJsonStr.find('\x00')])
        return json.loads(rawJsonStr[0:rawJsonStr.find('\x00')])
    else:
        print json.loads(rawJsonStr)
        return json.loads(rawJsonStr)

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

def handleERR(ts,dev,p1):
    errMsg=""
    if (p1==1):
        errMsg="UNKNOWN_CMD"
    elif (p1==2):
        errMsg="JSON_DECODING_FAILED"
    elif (p1==11):
        errMsg="TIME_NOT_SET"
    else:
        errMsg="UNHANDLED_EXCEPTION"
    print 'In handleERR',(ts,dev,errMsg)
    return True

def handleMSG(ts,addr,p1,v1,p2,v2):
    print 'In handleMSG', (ts,addr,p1,v1,p2,v2)
    endpoint=getEndpoint(addr)
    if (p2=="PSTAT"):
        setPINvalue(endpoint, p1, v1, "", "")
    elif (p2=="VSTAT"):
        setPINvalue(endpoint, "", "", p1, v1)
    else:
        print 'In handleMSG', (ts,addr,p1,v1,p2,v2)
    return True

def handleREP(ts,addr,msgTs,p1,v1,p2,v2):
    print 'In handleRep',(ts,addr,msgTs,p1,v1,p2,v2) 
    result = False
    endpoint=getEndpoint(addr)
    if (p1 and v1):
        if(p1.isdigit() and v1.isnumeric()):
            if(setPINvalue(endpoint,p1,v1)):
                result = updateCmdStatus(msgTs,'S')
        else:
            print 'Error: incorrect values'
    elif(p2 and v2):
                if(setPINvalue(endpoint,'V',None,p2,v2)):
                    result = updateCmdStatus(msgTs,'S')
    else:
        print "Required parameters have no value"
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

