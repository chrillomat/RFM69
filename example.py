#!/usr/bin/env python
from time import sleep
import RFM69
from RFM69registers import *

test = RFM69.RFM69(RF69_433MHZ, 0x01, 0x01, False)
print "class initialized"
#print "reading all registers"
#results = test.readAllRegs()
#for result in results:
#    print result
print "Performing rcCalibration"
test.rcCalibration()
#print "setting high power"
#test.setHighPower(True)
print "Checking temperature"
print test.readTemperature(0)
#print "sending blah to 0x02"
#test.send(0x02, "blah", False)
try:
    while True:
        print "sending"
        test.send(-1, [0x8E, 0x88, 0x8E, 0x88, 0x8E, 0x8E, 0x8E, 0x8E, 0xEE, 0x88, 0x88, 0xEE, 0x80, 0x00, 0x00, 0x00], False)
        sleep(.1)
        #print str(hex(test.readReg(REG_OPMODE)))
        #print str(hex(test.readReg(REG_IRQFLAGS1)))
except KeyboardInterrupt:
    print "user interrupted!"
finally:
    print "shutting down"
    test.shutdown()
