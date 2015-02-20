import sqlite3

class MYDB(object):
    def __init__(self,DB):
        self.db=DB
        self.con = None
        self.con=sqlite3.connect(self.db, timeout=2)
    def    close(self):
        self.con.close()
    def executeSelect(self,query,params):
        rows=None
        try:
            cur=self.con.cursor()
            cur.execute(query,params)
            rows=cur.fetchall()
        except sqlite3.Error, e:
            print "error %s:" % e.args[0]
        except sqlite3.OperationalError:
            print "Database is locked"
        except Exception, e:
            print repr(e)
        finally:
            return rows
    def executeSelectOne(self,query,params):
        row=None
        try:
            cur=self.con.cursor()
            cur.execute(query,params)
            row=cur.fetchone()
        except sqlite3.Error, e:
            print "error %s:" % e.args[0]
        except sqlite3.OperationalError:
            print "Database is locked"
        except Exception, e:
            print repr(e)
        finally:
            return row[0]
    def executeUpdate(self,query,params=None):
        result=True
        try:
            cur=self.con.cursor()
            if (params):
                cur.execute(query,params)
            else:
                cur.execute(query)
            self.con.commit()
        except sqlite3.Error, e:
            print "Error: %s" % e.args[0]
            result=False
        except sqlite3.OperationalError:
            print "Database is locked"
        except Exception, e:
            print repr(e)
            result=False
        finally:
            return result
    def executeInsert(self,query,params):
        result=True
        try:
            cur=self.con.cursor()
            cur.execute(query,params)
            self.con.commit()
        except sqlite3.Error, e:
            print "Error: %s" % e.args[0]
            result=False
        except sqlite3.OperationalError:
            print "Database is locked"
        except Exception, e:
            print repr(e)
            result=False
        finally:
            return result


        
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

def str2date(Str):
    if (Str[0].encode('ascii')<>'\x00'):
        print 'x'
        yyyy=Str[0:4]
        mm=Str[4:6]
        dd=Str[6:8]
        HH=Str[8:10]
        MI=Str[10:12]
        SS=Str[12:14]
        SSSSS=Str[14:20]
        return yyyy+'-'+mm+'-'+dd+' '+HH+':'+MI+':'+SS+'.'+SSSSS
    else:
        print 'y'
        return ""

def ByteToHex( byteStr ):
    """
    Convert a byte string to it's hex string representation e.g. for output.
    """
    
    # Uses list comprehension which is a fractionally faster implementation than
    # the alternative, more readable, implementation below
    #   
    #    hex = []
    #    for aChar in byteStr:
    #        hex.append( "%02X " % ord( aChar ) )
    #
    #    return ''.join( hex ).strip()        

    return ''.join( [ "%02X" % ord( x ) for x in byteStr ] ).strip()

#-------------------------------------------------------------------------------

def HexToByte( hexStr ):
    """
    Convert a string hex byte values into a byte string. The Hex Byte values may
    or may not be space separated.
    """
    # The list comprehension implementation is fractionally slower in this case    
    #
    #    hexStr = ''.join( hexStr.split(" ") )
    #    return ''.join( ["%c" % chr( int ( hexStr[i:i+2],16 ) ) \
    #                                   for i in range(0, len( hexStr ), 2) ] )
 
    bytes = []

    hexStr = ''.join( hexStr.split(" ") )

    for i in range(0, len(hexStr), 2):
        bytes.append( chr( int (hexStr[i:i+2], 16 ) ) )

    return ''.join( bytes )