#!/usr/bin/python

from RFM69registers import *
import spidev

def readReg(addr):
	return spi.xfer([addr & 0x7F, 0])[1]

def writeReg(addr, value):
	spi.xfer([addr | 0x80, value])

spi = spidev.SpiDev()
spi.open(0, 0)
spi.max_speed_hz = 4000000

print spi.mode

print readReg(REG_FIFO)
print readReg(REG_OPMODE)
print readReg(REG_BITRATEMSB)

