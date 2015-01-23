#!/usr/bin/env/python

from RFM69registers import *
import spidev

try:
    import RPIO
    RPIOsupport=True
except ImportError:
    RPIOsupport=False
    Logger.warn('RPIO not available - no hardware control')

import time

class RFM69():
  def __init__(self, freqBand, nodeID, networkID, isRFM69HW = False, intPin = 24):

    self.freqBand = freqBand
    self.address = nodeID
    self.networkID = networkID
    self.isRFM69HW = isRFM69HW
    self.intPin = intPin
    self.mode = ""
    self.promiscuousMode = False
    self.DATALEN = 0
    self.SENDERID = 0
    self.TARGETID = 0
    self.PAYLOADLEN = 0
    self.ACK_REQUESTED = 0
    self.ACK_RECEIVED = 0
    self.RSSI = 0
    self.DATA = []

    RPIO.setup(self.intPin, RPIO.IN) # this is ok

    frfMSB = {RF69_315MHZ: RF_FRFMSB_315, RF69_433MHZ: RF_FRFMSB_433,
              RF69_868MHZ: RF_FRFMSB_868, RF69_915MHZ: RF_FRFMSB_915}
    frfMID = {RF69_315MHZ: RF_FRFMID_315, RF69_433MHZ: RF_FRFMID_433,
              RF69_868MHZ: RF_FRFMID_868, RF69_915MHZ: RF_FRFMID_915}
    frfLSB = {RF69_315MHZ: RF_FRFLSB_315, RF69_433MHZ: RF_FRFLSB_433,
              RF69_868MHZ: RF_FRFLSB_868, RF69_915MHZ: RF_FRFLSB_915}

    self.CONFIG = {
      0x01: [REG_OPMODE, RF_OPMODE_SEQUENCER_ON | RF_OPMODE_LISTEN_OFF | RF_OPMODE_STANDBY],
      #no shaping
      0x02: [REG_DATAMODUL, RF_DATAMODUL_DATAMODE_PACKET | RF_DATAMODUL_MODULATIONTYPE_FSK | RF_DATAMODUL_MODULATIONSHAPING_00],
      #0x02: [REG_DATAMODUL, RF_DATAMODUL_DATAMODE_PACKET | RF_DATAMODUL_MODULATIONTYPE_OOK | RF_DATAMODUL_MODULATIONSHAPING_00],
      ##17241BPS
      #  0x03: [REG_BITRATEMSB, 7],
      #  0x04: [REG_BITRATELSB, 63],
      #9579BPS
        0x03: [REG_BITRATEMSB, 13],
        0x04: [REG_BITRATELSB, 13],

        0x05: [REG_FDEVMSB,0x05],
        0x06: [REG_FDEVLSB,0xC3],
        0x07: [REG_FRFMSB, 0xD9],
        0x08: [REG_FRFMID, 0x20],#0x20
        0x09: [REG_FRFLSB, 0x04],#0x04
        0x0B: [REG_AFCCTRL, 0x20],

      # looks like PA1 and PA2 are not implemented on RFM69W, hence the max output power is 13dBm
      # +17dBm and +20dBm are possible on RFM69HW
      # +13dBm formula: Pout=-18+OutputPower (with PA0 or PA1**)
      # +17dBm formula: Pout=-14+OutputPower (with PA1 and PA2)**
      # +20dBm formula: Pout=-11+OutputPower (with PA1 and PA2)** and high power PA settings (section 3.3.7 in datasheet)
      0x11: [REG_PALEVEL, RF_PALEVEL_PA0_ON | RF_PALEVEL_PA1_OFF | RF_PALEVEL_PA2_OFF | RF_PALEVEL_OUTPUTPOWER_11111],
      #over current protection (default is 95mA)
      #0x13: [REG_OCP, RF_OCP_ON | RF_OCP_TRIM_95],
      #  0x19: [REG_RXBW, RF_RXBW_DCCFREQ_010 | RF_RXBW_MANT_16 | RF_RXBW_EXP_2],
        0x19: [REG_RXBW, RF_RXBW_DCCFREQ_010 | RF_RXBW_MANT_16 | RF_RXBW_EXP_0],
        0x1A: [REG_AFCBW, RF_RXBW_DCCFREQ_010 | RF_RXBW_MANT_16 | RF_RXBW_EXP_0],
      #  0x1E: [REG_AFCFEI, 12],
      #  0x1E: [REG_AFCFEI, 0],
          0x1E: [REG_AFCFEI, 0x2C],
      # TX: packet sent
      0x25: [REG_DIOMAPPING1, RF_DIOMAPPING1_DIO0_00],
        0x29: [REG_RSSITHRESH, 190],#220
        0x2A: [REG_RXTIMEOUT1, 0],
        0x2B: [REG_RXTIMEOUT2, 0],
      0x2C: [REG_PREAMBLEMSB, 0],
        0x2D: [REG_PREAMBLELSB, 0x03],
      #  0x2E: [REG_SYNCCONFIG, RF_SYNC_ON | RF_SYNC_FIFOFILL_AUTO | RF_SYNC_SIZE_2 | RF_SYNC_TOL_0],
        0x2E: [REG_SYNCCONFIG, RF_SYNC_ON | RF_SYNC_FIFOFILL_MANUAL | RF_SYNC_SIZE_2 | RF_SYNC_TOL_0],
      #  0x2E: [REG_SYNCCONFIG, RF_SYNC_ON | RF_SYNC_FIFOFILL_AUTO | RF_SYNC_SIZE_1 | RF_SYNC_TOL_0],
        0x2F: [REG_SYNCVALUE1, 0x2D],
        0x30: [REG_SYNCVALUE2, 0xDA],

      0x37: [REG_PACKETCONFIG1, RF_PACKET1_FORMAT_FIXED | RF_PACKET1_DCFREE_OFF |
            RF_PACKET1_CRC_OFF | RF_PACKET1_CRCAUTOCLEAR_ON | RF_PACKET1_ADRSFILTERING_OFF],
        0x38: [REG_PAYLOADLENGTH, 16],
      #TX on FIFO not empty
      0x3C: [REG_FIFOTHRESH, RF_FIFOTHRESH_TXSTART_FIFONOTEMPTY | RF_FIFOTHRESH_VALUE],
        0X3D: [REG_PACKETCONFIG2, 2],
    }
    #initialize SPI
    self.spi = spidev.SpiDev()
    self.spi.open(0, 0)
    self.spi.max_speed_hz = 4000000

    #verify chip is syncing?
    while self.readReg(REG_SYNCVALUE1) != 0xAA:
      self.writeReg(REG_SYNCVALUE1, 0xAA)

    while self.readReg(REG_SYNCVALUE1) != 0x55:
      self.writeReg(REG_SYNCVALUE1, 0x55)

    #write config
    for value in self.CONFIG.values():
      self.writeReg(value[0], value[1])

    self.encrypt(0)
    self.setHighPower(self.isRFM69HW)
    # Wait for ModeReady
    while (self.readReg(REG_IRQFLAGS1) & RF_IRQFLAGS1_MODEREADY) == 0x00:
      pass

    RPIO.add_interrupt_callback(self.intPin, self.interruptHandler, edge='rising')
    RPIO.wait_for_interrupts(threaded=True)

  def setFreqeuncy(self, FRF):
    self.writeReg(REG_FRFMSB, FRF >> 16)
    self.writeReg(REG_FRFMID, FRF >> 8)
    self.writeReg(REG_FRFLSB, FRF)

  def setMode(self, newMode):
    if newMode == self.mode:
      return

    if newMode == RF69_MODE_TX:
      self.writeReg(REG_OPMODE, (self.readReg(REG_OPMODE) & 0xE3) | RF_OPMODE_TRANSMITTER)
      if self.isRFM69HW:
        self.setHighPowerRegs(True)
    elif newMode == RF69_MODE_RX:
      self.writeReg(REG_OPMODE, (self.readReg(REG_OPMODE) & 0xE3) | RF_OPMODE_RECEIVER)
      if self.isRFM69HW:
        self.setHighPowerRegs(False)
    elif newMode == RF69_MODE_SYNTH:
      self.writeReg(REG_OPMODE, (self.readReg(REG_OPMODE) & 0xE3) | RF_OPMODE_SYNTHESIZER)
    elif newMode == RF69_MODE_STANDBY:
      self.writeReg(REG_OPMODE, (self.readReg(REG_OPMODE) & 0xE3) | RF_OPMODE_STANDBY)
    elif newMode == RF69_MODE_SLEEP:
      self.writeReg(REG_OPMODE, (self.readReg(REG_OPMODE) & 0xE3) | RF_OPMODE_SLEEP)
    else:
      return

    # we are using packet mode, so this check is not really needed
    # but waiting for mode ready is necessary when going from sleep because the FIFO may not be immediately available from previous mode
    while self.mode == RF69_MODE_SLEEP and self.readReg(REG_IRQFLAGS1) & RF_IRQFLAGS1_MODEREADY == 0x00:
      pass

    self.mode = newMode;

  def sleep(self):
    self.setMode(RF69_MODE_SLEEP)

  def setAddress(self, addr):
    self.address = addr
    self.writeReg(REG_NODEADRS, self.address)

  def setPowerLevel(self, powerLevel):
    if powerLevel > 31:
      powerLevel = 31
    self.powerLevel = powerLevel
    self.writeReg(REG_PALEVEL, (readReg(REG_PALEVEL) & 0xE0) | self.powerLevel)

  def canSend(self):
    #if signal stronger than -100dBm is detected assume channel activity
    if self.mode == RF69_MODE_RX and self.PAYLOADLEN == 0 and self.readRSSI() < CSMA_LIMIT:
      self.setMode(RF69_MODE_STANDBY)
      return True
    return False

  def send(self, toAddress, buff, requestACK):
    self.writeReg(REG_PACKETCONFIG2, (self.readReg(REG_PACKETCONFIG2) & 0xFB) | RF_PACKET2_RXRESTART)
    now = time.time()
    while (not self.canSend()) and time.time() - now < RF69_CSMA_LIMIT_S:
      self.receiveDone()
    self.sendFrame(toAddress, buff, requestACK, False)

#    to increase the chance of getting a packet across, call this function instead of send
#    and it handles all the ACK requesting/retrying for you :)
#    The only twist is that you have to manually listen to ACK requests on the other side and send back the ACKs
#    The reason for the semi-automaton is that the lib is ingterrupt driven and
#    requires user action to read the received data and decide what to do with it
#    replies usually take only 5-8ms at 50kbps@915Mhz

  def sendWithRetry(self, toAddress, buff, retries, retryWaitTime):
    for i in range(0, retries):
      self.send(toAddress, buff, True)
      sentTime = time.time()
      while (time.time() - sentTime) * 1000 < retryWaitTime:
        if self.ACKReceived(toAddress):
          return True
      return False

  def ACKRecieved(self, fromNodeID):
    if self.receiveDone():
      return (self.SENDERID == fromNodeID or fromNodeID == RF69_BROADCAST_ADDR) and self.ACK_RECEIVED
    return False

  def ACKRequested(self):
    return self.ACK_REQUESTED and self.TARGETID != RF69_BROADCAST_ADDR

  def sendACK(self, buff):
    while not self.canSend():
      self.receiveDone()
    self.sendFrame(self.SENDERID, buff, False, True)

  def sendFrame(self, toAddress, buff, requestACK, sendACK):
    #turn off receiver to prevent reception while filling fifo
    self.setMode(RF69_MODE_STANDBY)
    #wait for modeReady
    while (self.readReg(REG_IRQFLAGS1) & RF_IRQFLAGS1_MODEREADY) == 0x00:
      pass
    # DIO0 is "Packet Sent"
    self.writeReg(REG_DIOMAPPING1, RF_DIOMAPPING1_DIO0_00)

    if (len(buff) > RF69_MAX_DATA_LEN):
      buff = buff[0:RF69_MAX_DATA_LEN]

    if toAddress>=0:
        self.spi.xfer([REG_FIFO | 0x80, len(buff) + 3, toAddress, self.address])

        if sendACK:
            self.spi.xfer([0x80])
        elif requestACK:
            self.spi.xfer([0x40])
        else:
            self.spi.xfer([0x00]) # TODO

            self.spi.xfer([int(ord(i)) for i in list(buff)])
    else:
        #print buff
        #self.spi.xfer(buff)
        for elem in buff:
            self.spi.xfer([REG_FIFO | 0x80, elem])
        for elem in buff:
            self.spi.xfer([REG_FIFO | 0x80, elem])
        for elem in buff:
            self.spi.xfer([REG_FIFO | 0x80, elem])

    self.setMode(RF69_MODE_TX)
    # interuptHandler will set chip to standby once TX is finished

  def interruptHandler(self, *args):
    # TODO for OOK
    print "int: " + str(time.time())
    if self.mode == RF69_MODE_RX:# and self.readReg(REG_IRQFLAGS2) & RF_IRQFLAGS2_PAYLOADREADY:
      self.setMode(RF69_MODE_STANDBY)
      self.spi.xfer([REG_FIFO & 0x7f])
      self.DATA = self.spi.xfer([0 for i in range(0, 15)])
      print self.DATA
      self.setMode(RF69_MODE_RX)
    elif self.mode == RF69_MODE_TX:
      self.setMode(RF69_MODE_STANDBY)
    # in any case, determine RSSI (DIO1 = RSSI in continuous mode
    self.RSSI = self.readRSSI()
    print self.RSSI

  def receiveBegin(self):
    self.DATALEN = 0
    self.SENDERID = 0
    self.TARGETID = 0
    self.PAYLOADLEN = 0
    self.ACK_REQUESTED = 0
    self.ACK_RECEIVED = 0
    self.RSSI = 0
    if (self.readReg(REG_IRQFLAGS2) & RF_IRQFLAGS2_PAYLOADREADY):
      # avoid RX deadlocks
      self.writeReg(REG_PACKETCONFIG2, (self.readReg(REG_PACKETCONFIG2) & 0xFB) | RF_PACKET2_RXRESTART)
    #set DIO0 to "PAYLOADREADY" in receive mode
    #self.writeReg(REG_DIOMAPPING1, RF_DIOMAPPING1_DIO0_10)
    self.writeReg(REG_DIOMAPPING1, RF_DIOMAPPING1_DIO0_01)
    self.setMode(RF69_MODE_RX)

  def receiveDone(self):
    if self.mode == RF69_MODE_RX and self.PAYLOADLEN > 0:
      self.setMode(RF69_MODE_STANDBY)
      return True
    elif self.mode == RF69_MODE_RX:
      # already in RX no payload yet
      return False
    self.receiveBegin()
    return False

  def readRSSI(self, forceTrigger = False):
    rssi = 0
    if forceTrigger:
      self.writeReg(REG_RSSICONFIG, RF_RSSI_START)
      while self.readReg(REG_RSSICONFIG) & RF_RSSI_DONE == 0x00:
        pass
    rssi = self.readReg(REG_RSSIVALUE) * -1
    rssi = rssi >> 1
    return rssi

  def encrypt(self, key):
    self.setMode(RF69_MODE_STANDBY)
    if key != 0 and len(key) == 16:
      self.spi.xfer([REG_AESKEY1 | 0x80] + [int(ord(i)) for i in list(key)])
      self.writeReg(REG_PACKETCONFIG2, 1)
    else:
      self.writeReg(REG_PACKETCONFIG2, 0)

  def readReg(self, addr):
    return self.spi.xfer([addr & 0x7F, 0])[1]

  def writeReg(self, addr, value):
    self.spi.xfer([addr | 0x80, value])

  def promiscuous(self, onOff):
    self.promiscuousMode = onOff

  def setHighPower(self, onOff):
    if onOff:
      self.writeReg(REG_OCP, RF_OCP_OFF)
      #enable P1 & P2 amplifier stages
      self.writeReg(REG_PALEVEL, (self.readReg(REG_PALEVEL) & 0x1F) | RF_PALEVEL_PA1_ON | RF_PALEVEL_PA2_ON)
    else:
      self.writeReg(REG_OCP, RF_OCP_ON)
      #enable P0 only
      self.writeReg(REG_PALEVEL, RF_PALEVEL_PA0_ON | RF_PALEVEL_PA1_OFF | RF_PALEVEL_PA2_OFF | powerLevel)

  def setHighPowerRegs(self, onOff):
    if onOff:
      self.writeReg(REG_TESTPA1, 0x5D)
      self.writeReg(REG_TESTPA2, 0x7C)
    else:
      self.writeReg(REG_TESTPA1, 0x55)
      self.writeReg(REG_TESTPA2, 0x70)

  def readAllRegs(self):
    results = []
    for address in range(1, 0x50):
      results.append([str(hex(address)), str(bin(self.readReg(address)))])
    return results

  def readTemperature(self, calFactor):
    self.setMode(RF69_MODE_STANDBY)
    self.writeReg(REG_TEMP1, RF_TEMP1_MEAS_START)
    while self.readReg(REG_TEMP1) & RF_TEMP1_MEAS_RUNNING:
      pass
    # COURSE_TEMP_COEF puts reading in the ballpark, user can add additional correction
    #'complement'corrects the slope, rising temp = rising val
    return int(~self.readReg(REG_TEMP2)) + COURSE_TEMP_COEF + calFactor


  def rcCalibration(self):
    self.writeReg(REG_OSC1, RF_OSC1_RCCAL_START)
    while self.readReg(REG_OSC1) & RF_OSC1_RCCAL_DONE == 0x00:
      pass

  def shutdown(self):
    self.setHighPower(False)
    self.sleep()
    RPIO.cleanup()
