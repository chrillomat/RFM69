#!/usr/bin/env python
#from time import sleep
import time
import RFM69
from RFM69registers import *

test = RFM69.RFM69(RF69_433MHZ, 0x01, 0x01, False)
test.setFrequency(867.8e6)
test.setBitrate(9579)
test.setFdev(90e3)

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
    val_old=0xFF
    test.receiveBegin()
    #while not test.receiveDone():
    while True:
        val=test.readReg(REG_IRQFLAGS1)
        if val!=val_old:
            print time.time()
            print str(hex(val))
            print str(hex(test.readReg(REG_IRQFLAGS2)))
            print str(hex(test.readReg(REG_AFCFEI)))
            print str(hex(test.readReg(REG_AFCMSB)))
            print str(hex(test.readReg(REG_AFCLSB)))
            print str(hex(test.readReg(REG_FEIMSB)))
            print str(hex(test.readReg(REG_FEILSB)))
        time.sleep(0.1)
        val_old=val
    print test.DATA
except KeyboardInterrupt:
    print "user interrupted!"
finally:
    print "shutting down"
    test.shutdown()
