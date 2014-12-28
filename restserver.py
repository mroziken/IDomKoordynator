#!/usr/bin/env python
import web
import json
import logging.handlers
import sqlite3
import collections
import time
import datetime
import sys
from collections import namedtuple



LOG_FILENAME = '/tmp/listener.log'
LOG_LEVEL = logging.INFO # Could be e.g. "DEBUG" or "WARNING"
DB='/home/michal/workspace/iDomKoordynator/dev.db'

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

def namedtuple_factory(cursor, row):
    """
    Usage:
    con.row_factory = namedtuple_factory
    """
    fields = [col[0] for col in cursor.description]
    Row = namedtuple("Row", fields)
    return Row(*row)

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

urls = (
    '/lights_on', 'lights_on',
    '/lights_off', 'lights_off',
    '/digital_read', 'digital_read',
    '/get_layout', 'get_layout',
    '/check_cmd_proc', 'check_cmd_proc'
)

app = web.application(urls, globals())

class returnObject:
    def __init__(self):
        self.result = True
        self.menuItems = []
        self.ts = datetime.datetime.now().isoformat(' ')
        
    def setResult(self,result):
        self.result = result
    def setMenuItems(self,menuItems):
        self.menuItems = menuItems
    def setTs(self,ts):
        self.ts = ts
    def setAll(self,result,ts,menuItems):
        self.result = result
        self.menuItems = menuItems
        self.ts = ts
    def getReturnObject(self):
        return {'result':self.result,'ts':self.ts,'menu':self.menuItems}
        
        


class check_cmd_proc:        
    def GET(self):
        return_obj=returnObject()
        user_data=web.input()
        ts=user_data.YY+'-'+user_data.MM+'-'+user_data.DD+' '+user_data.HH+':'+user_data.mm+':'+user_data.SS+'.'+user_data.ms
        if not cmdjrnlCheck(ts):
            return_obj.setResult(False)
        return json.dumps(return_obj.getReturnObject())

class lights_on:        
    def GET(self):
        return_obj=returnObject()
        cmd='1701'
        dev='mxm1'
        endpointDet=getEndpointDet(dev)
        devtype=endpointDet[0]
        address=endpointDet[1]
        ret=cmdjrnlWrite(devtype,address,cmd)
        if ret:
            return_obj.setTs(ret)
        else:
            return_obj.setResult(False)
        return json.dumps(return_obj.getReturnObject())

class lights_off:
    def GET(self):
        return_obj=returnObject()
        cmd="1700"
        dev='mxm1'
        endpointDet=getEndpointDet(dev)
        devtype=endpointDet[0]
        address=endpointDet[1]
        ret=cmdjrnlWrite(devtype,address,cmd)
        if ret:
            return_obj.setTs(ret)
        else:
            return_obj.setResult(False)
        return json.dumps(return_obj.getReturnObject())

class digital_read:
    def GET(self):
        return_obj=returnObject()
        cmd="\x10"
        dev='mxm1'
        endpointDet=getEndpointDet(dev)
        devtype=endpointDet[0]
        address=endpointDet[1]
        result=cmdjrnlWrite(devtype,address,cmd)
        print 'result',result
        #return_obj['menu']=objects_list
        #return_obj['result']=result
        return_obj.setResult(result)
        return json.dumps(return_obj.getReturnObject())

      
class get_layout:
    db = None
    rows = None
    def GET(self):
        return_obj=returnObject()
        objects_list=[]
        try:
            db = sqlite3.connect(DB)
            db.row_factory = namedtuple_factory
            c=db.cursor()
            c.execute('''SELECT UpperLevel, ElementName, ElementType, CommandOn,CommandOff, state FROM menu order by UpperLevel, ElementName''')
            rows = c.fetchall()
            for row in rows:
                d = collections.OrderedDict()
                d['UpperLevel'] = row.UpperLevel
                d['ElementName'] = row.ElementName
                d['ElementType'] = row.ElementType
                d['CommandOn'] = row.CommandOn
                d['CommandOff'] = row.CommandOff
                d['State']=row.state
                objects_list.append(d)
        except sqlite3.Error, e:
            print "error %s:" % e.args[0]
            return_obj.setResult(False)
        except:
            print "Unexpected error:", sys.exc_info()
            return_obj.setResult(False)
        finally:
            if db:
                db.close()
            
            return_obj.setMenuItems(objects_list)
            return json.dumps(return_obj.getReturnObject())
            
def cmdjrnlCheck(tsStr):
    db = None
    row = None
    result = False
    try:
        print 'In cmdjrnlCheck: '+tsStr
        db = sqlite3.connect(DB)
        db.row_factory = namedtuple_factory
        for i in range(0,9):
            #print i
            c=db.cursor()
            c.execute('''SELECT stat from cmdjrnl where ts=?''',(tsStr,))
            row=c.fetchone()
            if (row[0] == 'S'):
                result = True
                break
            time.sleep(.5)
    except sqlite3.Error, e:
        print "Error %s:" % e.args[0]
        result=False
    except:
        print "Unexpected error:", sys.exc_info()
    
    finally:
        if db:
            db.close()
        return result
        
def getEndpointDet(endpoint):
    db = None
    row = None
    try:
        print 'In getEndpointDet: '+endpoint
        db = sqlite3.connect(DB)
        db.row_factory = namedtuple_factory
        c=db.cursor()
        c.execute('''SELECT type, address from endpointaddr where endpoint=?''',(endpoint,))
        row=c.fetchone()
    except sqlite3.Error, e:
        print "Error %s:" % e.args[0]
    except:
        print "Unexpected error:", sys.exc_info()
    
    finally:
        if db:
            db.close()
        return row

def cmdjrnlWrite(devtype,address,cmd):
    print 'Writing to cmdjrnl:%s' % cmd
    stat='P'
    result=''

    try:    
        db = sqlite3.connect(DB)
        c = db.cursor()
        ts=datetime.datetime.now().isoformat(' ')
        c.execute('''INSERT INTO cmdjrnl(ts,devtype,address,cmd,stat) VALUES(?,?,?,?,?)''',(ts,devtype,address,cmd,stat))
        db.commit()
        result=ts
        
    except sqlite3.Error, e:
        print "Error %s:" % e.args[0]
    except:
        print "Unexpected error:", sys.exc_info()
    
    finally:
        if db:
            db.close()
        return result
    
    


if __name__ == "__main__":
    app.run()