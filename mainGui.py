import sys
from turtle import update
sys.path.insert(0, '/home/pi/.local/lib/python3.9/site-packages')

from re import X
from tkinter import Y
from PyQt5.QtWidgets import*
from PyQt5.QtCore import *
from PyQt5.uic import loadUi
from matplotlib.backends.backend_qt5agg import (NavigationToolbar2QT as NavigationToolbar)
import numpy as np
from numpy import random
import matplotlib.pyplot as plt
from itertools import count
import pandas as pd
from matplotlib.animation import FuncAnimation
from PyQt5 import QtWidgets

import time
import os
import Adafruit_GPIO.SPI as SPI
import Adafruit_MCP3008
import RPi.GPIO as GPIO

SPI_PORT   = 0
SPI_DEVICE = 0
mcp = Adafruit_MCP3008.MCP3008(spi=SPI.SpiDev(SPI_PORT, SPI_DEVICE))

GPIO.setmode(GPIO.BOARD)
GPIO.setup(12, GPIO.OUT)
GPIO.output(12, GPIO.LOW)

noiseCeiling = 0
noiseFloor = 0

class CalibrateWindow(QWidget):
    def __init__(self, *args, **kwargs):
        QWidget.__init__(self, *args, **kwargs)

        self.loadingBar = QtWidgets.QProgressBar()
        self.textInfoLabel = QtWidgets.QLabel()
        self.textInfoLabel.setText("Turn laser off to begin calibration...")
        self.textInfoLabel.setAlignment(Qt.AlignCenter)
        run_btn=QtWidgets.QPushButton("Calibrate")

        self.layout = QtWidgets.QVBoxLayout()
        self.layout.addWidget(self.loadingBar)
        self.layout.addWidget(self.textInfoLabel)
        self.layout.addWidget(run_btn)

        self.counter=0
        self.calArray = np.zeros(1000)

        run_btn.clicked.connect(self.button)

        self.setLayout(self.layout)
        self.show()

    def button(self):
        global noiseCeiling, noiseFloor
        if self.counter==0:
            for x in range(len(self.calArray)):
                self.calArray[x] = mcp.read_adc(0)
                self.loadingBar.setValue(int(50*x/len(self.calArray)))
            noiseFloor = np.mean(self.calArray) + 2*np.std(self.calArray)
            self.textInfoLabel.setText("Turn laser on")
        elif self.counter==1:
            for x in range(len(self.calArray)):
                self.calArray[x] = mcp.read_adc(0)
                self.loadingBar.setValue(int(50+50*x/len(self.calArray)))
            noiseCeiling = np.mean(self.calArray) - 2*np.std(self.calArray)
            self.close()
        self.counter+=1


class MatplotlibWidget(QMainWindow):
    
    def __init__(self):
        QMainWindow.__init__(self)
        loadUi("mainWindow6.ui",self)
        self.setWindowTitle("Particle Counter")

        self.pwm = GPIO.PWM(12, 1000) # Set Frequency to 1 KHz
        self.pwm.start(self.fanProgressBar.value()) 

        self.partCounter = np.zeros(3)

        self.update_timer = QTimer()
        self.update_timer.setInterval(int(1000)) 
        self.update_timer.timeout.connect(self.update_TimerLabel)

        self.update_Hist = QTimer()
        self.update_Hist.setInterval(int(600)) 
        self.update_Hist.timeout.connect(self.update_display1)
        

        self.fanUpButton.clicked.connect(self.fanUp)
        self.fanDownButton.clicked.connect(self.fanDown)
        self.resetButton.clicked.connect(self.resetCounter)
        self.switchDisplayButton.clicked.connect(self.startPause)

        self.worker = WorkerThread()
        self.readADC = QTimer()
        self.readADC.setInterval(int(15)) 
        self.readADC.timeout.connect(self.worker.start)
        self.worker.update_SmallCount.connect(self.evt_UpdateSmallCount)
        self.worker.update_MediumCount.connect(self.evt_UpdateMediumCount)
        self.worker.update_LargeCount.connect(self.evt_UpdateLargeCount)
        

    def update_TimerLabel(self):
        self.timerDisp.display(self.timerDisp.intValue()+1)
        
    def evt_UpdateSmallCount(self):
        self.partCounter[0] += 1
        
    def evt_UpdateMediumCount(self):
        self.partCounter[1] += 1
        
    def evt_UpdateLargeCount(self):
        self.partCounter[2] += 1

    def startPause(self):
        counter = 0
        if counter == 0:
            self._new_window = CalibrateWindow()
            self._new_window.show()
            self.readADC.start()
            self.update_timer.start()
            self.update_Hist.start()
            counter+=1
        if self.update_timer.isActive():
            self.switchDisplayButton.setText("Start")
            self.textInfo.setText("System Paused")
            self.update_timer.stop()
            self.update_Hist.stop()
            self.readADC.stop()
        else:
            
            self.switchDisplayButton.setText("Pause")
            self.textInfo.setText("Running...")
            self.update_timer.start()
            self.update_Hist.start()
            self.readADC.start()

    def fanUp(self):
        if self.fanProgressBar.value() < 100:
            self.fanProgressBar.setValue(self.fanProgressBar.value()+5)
            self.pwm.ChangeDutyCycle(self.fanProgressBar.value())
            
    def fanDown(self):
        if self.fanProgressBar.value() > 0:
            self.fanProgressBar.setValue(self.fanProgressBar.value()-5)
            self.pwm.ChangeDutyCycle(self.fanProgressBar.value())

    def resetCounter(self):

        self.partCounter[0] = 0
        self.partCounter[1] = 0
        self.partCounter[2] = 0

        self.updateCounter()
        self.timerDisp.display(0)

    def update_display1(self):
        self.MplWidget.canvas.axes.clear()
        self.MplWidget.canvas.axes.bar(np.arange(len(self.partCounter)), self.partCounter)#, color = (0.5,0.1,0.5,0.6)
        self.MplWidget.canvas.axes.set_xlabel('Particle Size')
        self.MplWidget.canvas.axes.set_ylabel('Number of Particles')
        self.MplWidget.canvas.axes.set_xticks(np.arange(len(self.partCounter)), ('Small', 'Medium', 'Large')) 
        self.MplWidget.canvas.axes[0].set_color('#2F528F')
        self.MplWidget.canvas.axes[1].set_color('#FCDCA4')
        self.MplWidget.canvas.axes[2].set_color('#A9D18E')
        self.MplWidget.canvas.draw()
        self.updateCounter()
    
    def updateCounter(self):

        self.smallCounterDisp.display(self.partCounter[0])
        self.mediumCounterDisp.display(self.partCounter[1])
        self.largeCounterDisp.display(self.partCounter[2])
        self.totalCounterDisp.display(np.sum(self.partCounter))



class WorkerThread(QThread):
    update_SmallCount = pyqtSignal(bool)
    update_MediumCount = pyqtSignal(bool)
    update_LargeCount = pyqtSignal(bool)
    
    def run(self):
        voltage = mcp.read_adc(0)
        minValue = voltage
        if (voltage<743):
            for x in range(1):
                voltage= mcp.read_adc(0)
                if voltage<minValue:
                    minValue = voltage
                    
            if ((minValue >= 701) and (minValue < 743)):
                    self.update_SmallCount.emit(1)
            elif ((minValue >= 578) and (minValue < 701)):
                    self.update_MediumCount.emit(1)
            elif ((minValue >= 365) and (minValue < 578)):
                    self.update_LargeCount.emit(1)



app = QApplication([])
window = MatplotlibWidget()
window.show()
app.exec_()