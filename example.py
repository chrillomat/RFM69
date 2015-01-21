#!/usr/bin/env python
from time import sleep
import RFM69
from RFM69registers import *

test = RFM69.RFM69(RF69_868MHZ, 0x01, 0x01, False)
print "class initialized"
print "reading all registers"
results = test.readAllRegs()
for result in results:
    print result
print "Performing rcCalibration"
test.rcCalibration()
#print "setting high power"
#test.setHighPower(True)
print "Checking temperature"
print test.readTemperature(0)
#print "sending blah to 0x02"
#test.send(0x02, "blah", False)
try:
    print "reading"
    test.receiveBegin()
    #while not test.receiveDone():
    while True:
        val=test.readReg(REG_IRQFLAGS1)
        if val==216:
            #pass
            print '.'
            #print test.readRSSI(True)
            #print test.readReg(REG_AFCFEI)
        else:
            print str(hex(val))
            print str(hex(test.readReg(REG_IRQFLAGS2)))
        sleep(0.1)
    print test.DATA
except KeyboardInterrupt:
    print "user interrupted!"
finally:
    print "shutting down"
    test.shutdown()
