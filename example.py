#!/usr/bin/env python
from time import sleep
import RFM69
from RFM69registers import *

test = RFM69.RFM69(RF69_433MHZ, 0x01, 0x01, False)
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
#print "setting encryption"
#test.encrypt("1234567891011121")
#print "sending blah to 0x03"
#test.send(0x03, "blah", True)
try:
    print "reading"
    test.receiveBegin()
    while not test.receiveDone():
	sleep(1)
	#val=test.readRSSI(True)
        val=str(hex(test.readReg(REG_IRQFLAGS1)))
        print val
    print test.DATA
except KeyboardInterrupt:
    print "user interrupted!"
finally:
    print "shutting down"
    test.shutdown()
