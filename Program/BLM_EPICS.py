#!/usr/bin/env python
# created from Anna Stampfli PSI. July 2021
# for Beam Loss Project
from pcaspy import Driver, SimpleServer

import threading # to run subprocesses, like image processing
#import queue #to make a queue of tasks
import logging #to mkae a log file
import traceback # for what??
import csv #for saving csv files
import json #for saving .json files
import subprocess #for running command line
import os #for the working directory

import functions as f
from parameters import *
import RPi.GPIO as GPIO
from pypylon import pylon
import numpy as np
import time
import cv2 as cv #for thresholding BitMask
import matplotlib.pyplot as plt
import sys
sys.settrace

#____________________Parameters_____________________


#Camera
Pformat = ['Mono8', 'Mono12', 'Mono12p']
SenBitD = ['Bpp8', 'Bpp10', 'Bpp12']
PVlimits = ['lolo', 'low', 'high', 'hihi']



#files to read in
"""
'../Calibration_Data/Position/_last_position.json'
'../Calibration_Data/Flatfield/_last_DarkI.npy'
'../Calibration_Data/Flatfield/_last_CalI.npy'
'../Calibration_Data/Flatfield/_last_CalA.npy'
'../Calibration_Data/BitMask/_last_bitmask.npy'
'../Calibration_Data/BitMask/_last_BM_Cal_parameters.json'
'../Calibration_Data/Dark/_last_DarkI.npy'
'../Calibration_Data/Dark/_last_Dark_parameters.json'
"""


#_____________________________________________________

#get the Hostname to change the EPICS previx
com = subprocess.Popen(["hostname"], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
output, errors = com.communicate()
com.wait()
print(errors)#logger?
BLM_NR = output[-3:-1]

#PATHS
CWD = os.getcwd()
print('Current working directory', CWD)
PATH_BM = os.path.join(CWD,'../Calibration_Data/BitMask/')
PATH_Pos = os.path.join(CWD,'../Calibration_Data/Position/')
PATH_Dark = os.path.join(CWD,'../Calibration_Data/Dark/')
PATH_Cal = os.path.join(CWD,'../Calibration_Data/Flatfield/')
PATH_LEDCal = os.path.join(CWD,'../Calibration_Data/LED_Calibration/')
PATH_sav = os.path.join(CWD,'../Data/EPICS_GUI/')
f.newdir(PATH_BM)
f.newdir(PATH_Pos)
f.newdir(PATH_Dark)
f.newdir(PATH_Cal)
f.newdir(PATH_LEDCal)
f.newdir(PATH_sav)

#logger setup
logging.basicConfig(format='%(asctime)s | %(levelname)s | %(name)s:%(message)s', datefmt='%d/%m/%Y %H:%M:%S %p', level=logging.INFO, 
filename='ARIDI-BLM' + BLM_NR + '.log')
logger = logging.getLogger("blm")
#logging.debug('') => for debugging purposes in development
#logging.info('') => something interesting, but expected happened: a PV changes
#logging.warning('') => when something unexpected or unusual: a PV changes but can't be set on this value
#logging.error => for things that go wrong but are usually recoverable
logging.info('STARTED SERVER ;) ;) :) ;) ;) :) ;) ;) :)')



prefix = 'ARIDI-BLM' + BLM_NR + ':' #'ARIDI-BLM01:'
pvdb = {
    'LEDA' : {'type' : 'int', #usage like boolean
                  'count' : 21,
                  'scan' : 1, #for reloading in the GUI
                  'value' : [0,0,0,0,0,0,0,
                             0,0,0,0,0,0,0,
                             0,0,0,0,0,0,0],
    },
    'LEDall' : {'tpye' : 'int', #usage like boolean
                'value' : 0,
    },
    
    'connect' : {'type' : 'int', #usage like boolean
                 'value' : 0,
    },
    'isConnected' : {'type' : 'int', #usage like boolean
                     'scan' : 1,
                     'value' : 0, 
    },
    
    'CAM-Pformat' : {'type' : 'enum', #only when not grabbing
                     'scan' : 1,
                     'enums' : Pformat,
                     'value' : 0,
    },
    'CAM-SenBitD' : {'type' : 'enum', #only when not grabbing
                     'scan' : 1,
                     'enums' : SenBitD,
                     'value' : 0,
                    },
    'CAM-acqFR' : {'type' : 'float',
                    'scan' : 1,
                   'prec' : 2,
                    'value' : 0,
                   'unit' : 'fps',
    },
    'CAM-EacqFR' : {'type' : 'int', #usage like boolean
                    'scan' : 1, 
                    'value' : 1,
    },
    'CAM-FR' : {'type' : 'float', #Resulting Frame Rate
                  'scan' : 1,
                'prec' : 2,
                  'value' : 0,
                'unit' : 'fps',
    },
    'CAM-EXPT' : { 'type' : 'int',
                  'scan' : 1,
                  'unit' : 'us', 
    },
    'CAM-GAMMA' : {'type' : 'float',
                   'scan' : 1,
                   'prec' : 2,
                   'value' : 1.00, 
    },
    'CAM-GAIN' : {'type' : 'float',
                  'scan' : 1,
                  'prec' : 2,
                  'value' : 0.00,
                  'unit' : 'dB',
    },
    
    'CAM-measure' : {'type' : 'int', #usage like boolean
                           'value' : 0,
                          },
    'CAM-isGrabbing' : {'type' : 'int', #usage like boolean
                           'value' : 0,
                         #'scan' : 1,
    },
    'Meas-delay' : {'type' : 'float', #read and write
                    'scan' : 1,
                    'value' : 0,
                    'prec' : 3,
                    'unit' : 'sec',
                    'lolim' : -1, 'hilim' : 99,
    },
    'Meas-time' : {'type' : 'float', #read only
                   'value' : 0,
                   'prec' : 0,
                   'unit' : 'us',
    },
                   
    'CAM-IMAGE' : {'type' : 'int',
                   'scan' : 3, 
                   'count' : 300*480, 
    },
    'CAM-IMAGEx' : {#'type' : 'int', #sliced size
                         'value' : Lx,
                         'count' : 1, 
    },
    'CAM-IMAGEy' : {'type' : 'int', #sliced size
                         'value' : Ly,
                         'count' : 1, 
    },
    
    'CAM-X_START' : {'type' : 'int',
                   'scan' : 1,
                   'value' : 0,
                   'unit' : 'Pixel',
                   'lolim' : 0, 'hilim' : 100,
    },
    'CAM-X_END' : {'type' : 'int',
                   'scan' : 1,
                   'value' : 480,
                   'unit' : 'Pixel',
                   'lolim' : 380, 'hilim' : 480,
    },
    
    'CAM-Y_START' : {'type' : 'int',
                   'scan' : 1,
                   'value': 0,
                   'unit' : 'Pixel',
                   'lolim' : 0, 'hilim' : 100,
    },
    'CAM-Y_END' : {'type' : 'int',
                   'scan' : 1,
                   'value' : 300,
                   'unit' : 'Pixel',
                   'lolim' : 200, 'hilim' : 300,
                  },
    
    'CAM-applyPOS' : {'type' : 'int', #usage like boolean
                 'value' : 0,
    },
    
    'POS-applied' : {'type' : 'int', #usage like boolean
                 'value' : 1,
                 #'scan' : 1
    },
    'POS-Time' : {
        'type' : 'string',
#        'value' :  pos_json['Time'],
    },
    
    'CAM-WIDTH' : {'type' : 'int',
                   'scan' : 1,
                   'value' : 480,#read from camera
                   'unit' : 'Pixel',
    },
    'CAM-HEIGHT' : {'type' : 'int',
                   'scan' : 1,
                   'value' : 300,#read from camera
                   'unit' : 'Pixel',
    },
  
    
    'LOSS' : {'type' : 'float',
              'prec' : 1,
              #'scan' : 1,
              'value' : -1,
              'count' : splits[0]*splits[1]+1,
             },
    
    'CalI' : {'type' : 'float',
               'prec' : 2,
               'value' : np.zeros(Lx*Ly), 
               'count' : 300*480, #max of size
#               'value' : CalI.flatten(),
               'scan' : 10 #to display it even when GUI is reloaded
    },
    
    'CalA' : { #Correction Array
        'type' : 'float', #usage as boolean array
        'prec' : 5,
        'count' : splits[0]*splits[1], #28
#        'value' : CalA.flatten(),
    },
    'useCalA': {
        'type' : 'int', #usage as boolean
        'value' : 0,
    },
    'CalA-LED' : {
        'type' : 'int', #usage as boolean
    },
    
    'BM_Cal-EXPT' : {
        'type' : 'int',    
        'unit' : 'us',
    },
    
    'BM_Cal-Time' : {
        'type' : 'string',
    },
    'BM_Cal-NR' : {
        'type' : 'int',    
        'value' : 0,
    },
    
    'CAM-acq_BM_Cal' : {
        'type' : 'int', #usage as boolean
        'value' : 0,  
        'scan' : 1,
    },
    
    'BitMask' : {
        'type' : 'int', #usage as boolean array
        'count' : Lx*Ly,#300*480,
        'scan' : 10 #to display it even when GUI is reloaded
    },
    'useBitMask': {
        'type' : 'int', #usage as boolean
        'value' : 0,
    },
    'BitMask-TH' : { #Bitmask threshhold
        'type' : 'int',
    },

      
    'CAM-acqDark' : {
        'type' : 'int', #usage as boolean
        'value' : 0,
        'scan' : 1,
    },
    'DarkI' : {'type' : 'float',
               'prec' : 2,
               'value' : np.zeros(Lx*Ly), 
               'count' : 300*480, #max of size
               'scan' : 10 #to display it even when GUI is reloaded
    },
    'Dark-EXPT' : {
        'type' : 'int',    
        'unit' : 'us',
    },
    'Dark-Time' : {
        'type' : 'string',
    },
    'Dark-NR' : {
        'type' : 'int',    
        'value' : 0,
    },
    'useDark': {
        'type' : 'int', #usage as boolean
        'value' : 0,
    },

    'SatA' : {
        'type' : 'int', 
        'count' : splits[0]*splits[1], #28
        'scan' : 1,
    },
    
    'CAM-acq_LEDCal' : {
        'type' : 'int', #usage as boolean
        'value' : 0,  
        'scan' : 1,
    },
    
    'LEDCal-NR' : {
        'type' : 'int',    
        'value' : 0,
    },
    
    'LEDCal-EXPT' : {
        'type' : 'int',    
        'unit' : 'us',
    },
    
    'LEDCal-Time' : {
        'type' : 'string',
    },
    
    'LEDCal-Next' : {
        'type' : 'int', #usage as boolean
        'value' : 0,  
        'scan' : 1,
    },
    
    'LEDCalI' : {'type' : 'float',
               'prec' : 2,
               'value' : np.zeros(Lx*Ly), 
               'count' : 300*480, #max of size
#               'value' : CalI.flatten(),
               'scan' : 10 #to display it even when GUI is reloaded
    },
    
    'LEDCalA' : { #Correction Array
        'type' : 'float', #usage as boolean array
        'prec' : 5,
        'count' : splits[0]*splits[1], #28
#        'value' : CalA.flatten(),
    },
    'useLEDCalA': {
        'type' : 'int', #usage as boolean
        'value' : 0,
    },
    
    
    'save': {
        'type' : 'int', #usage as boolean
        'value' : 0,
    },
        
    'MeanP': {'type' : 'float',
              'prec' : 3,
              'value' : 0,
    },
    
    'EdgeLoss': {'type' : 'float',
              'prec' : 3,
              'value' : 0,
    },
    'EdgeLossN': {'type' : 'float',
              'prec' : 3,
              'value' : 0,
    },
    'useEdgeDarkCor': { #use Dark Correction
        'type' : 'int', #usage as boolean
        'value' : 0,
    },
    
    'useEdgeCor': { #use Image Correction
        'type' : 'int', #usage as boolean
        'value' : 0,
    },
    'EdgeLoss0': {
        'type' : 'float',
        'prec' : 3,
#        'value' : EdgeLoss0,
    },
    'CAM-Temp': {
        'type' : 'float',
        'prec' : 3,
        'value' : 0,
        'unit' : 'C Coreboard',
        'scan' : 1,
    },
    
}
      
LEDdir = {}
for i in range(21):
    LEDdir['LED_'+str(i+1)] = {'type' : 'int', #usage like boolean
                              'value' : 0,
                              'scan' : 1, #execute the read function reguarly
                             }

LOSSdir = {}    
for i in range(splits[0]*splits[1]):
    LOSSdir['LOSS'+str(i+1)] = {'type' : 'float',
                                'prec' : 1,
                                'value' : -1,
                                'low' : -100, 'high' : 100, #Data limit for low / high alarm, -> Warning
                                'lolo' : -200, 'hihi' : 1000000, #Data limit for low low / high high alarm, -> Alarm
                             'lolim' : -200, 'hilim' : 13304655, #Data limit for graphics Display, complete Saturation for ROI 57x57=3249Pix Mono12
                               }
    for limit in PVlimits:
        LOSSdir['LOSS'+str(i+1)+'_'+limit] = {} #create LOSS1_high PV...


        
CalAdir = {} 
for i in range(splits[0]*splits[1]):
    CalAdir['CalA'+str(i+1)] = {'type' : 'float',
#                                'value' : CalA.flatten()[i],
                                  'prec' : 3,
                               }        

DarkAdir = {} 
#DarkA_flatten = DarkA.flatten()
for i in range(splits[0]*splits[1]):
    DarkAdir['DarkA'+str(i+1)] = {'type' : 'float',
#                                'value' : DarkA.flatten()[i],
                                  'prec' : 2,
                               }
    
DarkA_BMdir = {} #Dark Array with bitmask
for i in range(splits[0]*splits[1]):
    DarkAdir['DarkA_BM'+str(i+1)] = {'type' : 'float',
#                                'value' : DarkA_BM.flatten()[i],
                                  'prec' : 2,
                               }
    
SatAdir = {}
for i in range(splits[0]*splits[1]):
    SatAdir['SatA'+str(i+1)] = {'type' : 'int',
#                                'value' : BitMask_json['Saturation Array'][i],
                               }
    
ChlAdir = {}
for i in range(splits[0]*splits[1]):
    ChlAdir['ChlA'+str(i+1)] = {'type' : 'int', #usage as boolean
#                                'value' : BM_Cal_json['Saturation Array'][i],
                               }
    
LEDCalAdir = {} 
for i in range(splits[0]*splits[1]):
    LEDCalAdir['LEDCalA'+str(i+1)] = {'type' : 'float',
#                                'value' : CalA.flatten()[i],
                                  'prec' : 2,
                               }
    
LEDFAKTORdir = {} 
for i in range(splits[0]*splits[1]):
    LEDFAKTORdir['LEDFAKTOR'+str(i+1)] = {'type' : 'float',
#                                'value' : CalA.flatten()[i],
                                  'prec' : 3,
                               }

pvdb.update(LEDdir)  # To add two dictionary  
pvdb.update(LOSSdir) 
pvdb.update(CalAdir)
pvdb.update(DarkAdir)
pvdb.update(DarkA_BMdir)
pvdb.update(SatAdir)
pvdb.update(ChlAdir)
pvdb.update(LEDCalAdir)
pvdb.update(LEDFAKTORdir)

class iocDriver(Driver):

    def __init__(self):
        super(iocDriver, self).__init__()
    
            #GPIO setup
        GPIO.setwarnings(False)
        GPIO.setmode(GPIO.BOARD)
        GPIO.setup(LED_all, GPIO.OUT)
        
        self.loadCdata()
           
        
        #set limit PV, LOSS1_lolo, LOSS1_low, ...
        for i in range(splits[0]*splits[1]):
            PV = 'LOSS'+str(i+1)
            for limit in PVlimits:
                dirPV = self.getParamInfo(PV)
                self.setParam(PV+'_'+limit, dirPV[limit])
                
                      
                
    def write(self, reason, val): #caput
        status = True #determines if the value is written 
        false_val = False #sets to True if a value is wrong for a PV
        
        #what to do when value of a specific reason (PV Name) changes:   
        if reason == 'LEDA': 
            j = 0
            for i in val:
                if i == True:
                    GPIO.output(LED_all[j], GPIO.HIGH)
                elif i == False:
                    GPIO.output(LED_all[j], GPIO.LOW)
                else:
                    false_val = True
                j += 1
                
        elif reason == 'LEDall':
            if val == True:
                GPIO.output(LED_all, GPIO.HIGH)
           
            elif val == False:
                GPIO.output(LED_all, GPIO.LOW)
            else:
                false_val = True

        elif reason[0:4] == 'LED_':
            name,nr = reason.split('_')
            if val == True:
                GPIO.output(LED_all[int(nr)-1], GPIO.HIGH)
            elif val == False:
                GPIO.output(LED_all[int(nr)-1], GPIO.LOW)
            else:
                false_val = True

                
        elif reason == 'connect':
            if val == True:
                try:
                    #Camera setup
                    self.camera = pylon.InstantCamera(pylon.TlFactory.GetInstance().CreateFirstDevice())
        
                    self.camera.Open()
                    self.default_settings()
                    self.setParam('isConnected', True)
                    self.updatePVs()
                except Exception as e:
                    print('Error connect:',e)
                    logging.error('could not connect to the camera \n', e)
                    return False
                #print("Using device: ", self.camera.GetDeviceInfo().GetModelName())
                logging.info('*** Using device: %s ***' , self.camera.GetDeviceInfo().GetModelName())
            elif val == False:
                if self.getParam('CAM-measure') == True:
                    self.write('CAM-measure', False)# code from CAM-measure == False
                self.camera.Close()
                self.setParam('isConnected', False)
                self.updatePVs()
                #print("Camera connection closed")
                logging.info('*** Camera connection closed, Measurement stopped, if running ***')
            else:
                false_val = True
                
        elif reason[0:3] == 'CAM' and self.getParam('isConnected') == False:
            logging.warning("\n______________________________________________________\n\nCamera is not connected, so can not write any CAM Variables, first try connect and check is Connected \n______________________________________________________\n")
            #print('Camera is not connected, so can not write any CAM Variables, first try connect and check is Connected')
            return False
  
        elif reason == 'CAM-Pformat': # can only be changed, when camera not measuring
            if self.getParam('CAM-isGrabbing') == False and self.getParam('isConnected'):
                #print(val, Pformat[val])
                self.camera.PixelFormat = Pformat[val]
            else:
                logging.warning('can not change PV %s when Camera is measuring', reason)
                #print('can not change when Camera not connected or measuring.')
                
        elif reason == 'CAM-SenBitD': # can only be changed, when camera not measuring
            if self.getParam('CAM-isGrabbing') == False and self.getParam('isConnected'):
                #print(val, SenBitD[val])
                self.camera.BslSensorBitDepth = SenBitD[val]
            else:
                logging.warning('can not change PV %s when Camera is measuring', reason)
                #print('can not change when Camera not connected or measuring.')
                
        elif reason == 'CAM-acqFR':
            if 0.1 <= val < 1000000:
                self.camera.AcquisitionFrameRate = val
            else:
                false_val = True
                
        elif reason == 'CAM-EacqFR':
            if val == True or val == False:
                self.camera.AcquisitionFrameRateEnable = bool(val)                
            else:
                false_val = True       
                                                
        elif reason == 'CAM-EXPT':
            if 19 <= val <= 10000000 : #limits in pylon viewer, 19us-10s
                self.camera.ExposureTime = val
            else:
                false_val = True
                
        elif reason == 'BM_Cal-EXPT' or reason == 'LEDCal-EXPT':
            if 19 <= val <= 10000000 : #limits in pylon viewer, 19us-10s
                status = True
            else:
                false_val = True
                            
        elif reason == 'CAM-GAMMA':
            if 0 <= val < 4.0:
                self.camera.Gamma = val
            else:
                false_val = True
                           
        elif reason == 'CAM-GAIN':
            if 0.0 <= val < 48.000:
                self.camera.Gain.SetValue(float(val))
            else:
                false_val = True

        elif reason == 'CAM-measure':
            if val == True and self.getParam('CAM-isGrabbing') == False:
                # Camera Measurement Thread
                self.CAM_thread = threading.Thread(target = self.measurement, daemon = True)
                self.setParam('CAM-isGrabbing', True)
                self.updatePVs()
                self.CAM_thread.start()
                logging.info("\n______________________________________________________\n\nCamera started measuring with following Parameters: \n Exposure Time: %s \n Gain: %s \n Pixel Format: %s \n Sensor Bit Depth: %s \nImage Processing Parmaters: \n use BitMask: %s \n use Dark: %s \n use Calibration Faktor: %s \n______________________________________________________\n", self.getParam('CAM-EXPT'), self.getParam('CAM-GAIN'), self.getParam('CAM-Pformat'), self.getParam('CAM-SenBitD'), self.getParam('useBitMask'), self.getParam('useDark'), self.getParam('useCalA'))
               
            elif val == False and self.getParam('CAM-isGrabbing') == True:
                self.setParam('CAM-isGrabbing', False)
                self.updatePVs()
                self.CAM_thread.join() #really waits until the thread is finished
                logging.info("\n______________________________________________________\n\nCamera stopped measuring \n______________________________________________________\n")
            else:
                false_val = True
        
        elif reason == 'CAM-acq_BM_Cal': # can only be changed, when camera not measuring
            if val == True and self.getParam('CAM-isGrabbing') == False:
                #acquire BitMask Calibration Thread
                self.BM_Cal_thread = threading.Thread(target = self.acq_BM_Cal, daemon = True)
                self.setParam('CAM-isGrabbing', True)
                self.updatePVs()
                self.BM_Cal_thread.start()     
            else:
                logging.warning('can not acquire BitMask and Calibration, when Camara is measuring.')
                #print('can not acquire BitMask when Camera not connected or measuring.') 
                return False
                
        elif reason == 'CAM-acqDark': # can only be changed, when camera not measuring
            if val == True:
                # acquire Dark Thread
                self.Dark_thread = threading.Thread(target = self.acqDark, daemon = True)
                self.Dark_thread.start()     
            else:
                logging.warning('can not acquire Dark, when Camara is measuring.')
                #print('can not acquire Dark when Camera not connected or measuring.') 
                return False
            
        elif reason == 'CAM-acq_LEDCal': # can only be changed, when camera not measuring
            if val == True and self.getParam('CAM-isGrabbing') == False:
                # acquire LEDCal Thread
                self.LEDCal_thread = threading.Thread(target = self.acq_LEDCal, daemon = True)
                self.LEDCal_thread.start()     
            else:
                logging.warning('can not acquire LEDCal, when Camara is measuring.')
                #print('can not acquire Dark when Camera not connected or measuring.') 
                return False
            
        elif reason == 'Dark-NR':
            #status already true
            status=True
        elif reason == 'useBitMask':
            if not (val == True or val == False):
                false_val = True
                
        elif reason == 'BitMask-TH':
            if not 0 <= val <= 4095: #12bit 
                 false_val = True
        elif reason == 'BM_Cal-NR':
            #status already true
            status=True
       
        elif reason == 'CAM-X_START':
            self.x_start = val
            self.set_IMAGExy()
            
        elif reason == 'CAM-X_END':
            self.x_end = val
            self.set_IMAGExy()
            
        elif reason == 'CAM-Y_START':
            self.y_start = val
            self.set_IMAGExy()
        
        elif reason == 'CAM-Y_END':
            self.y_end = val
            self.set_IMAGExy()
            
        elif reason == 'CAM-applyPOS':
            if val == True:
                #calculates new sliced Dark, sliced Bitmasks, Edgelosses on base of current Data
                self.setParam('CAM-applyPOS', 1)
                self.updatePVs()
                self.loadCdata(newPOS=True)
                val = 0
            if not val == False:
                false_val = True
                
            
                
        elif reason == 'useDark':
            if not (val == True or val == False):
                false_val = True
                
        elif reason == 'useCalA':
            if not (val == True or val == False):
                false_val = True
                
        elif reason == 'useEdgeDarkCor':
            if not (val == True or val == False):
                false_val = True
        
        elif reason == 'useEdgeCor':
            if not (val == True or val == False):
                false_val = True
                
        elif reason == 'Meas-delay':
            if not 0 <= val <= 360: #not longer than 5min 
                false_val = True
       
        elif reason == 'save':
            if val == True:
                self.time_sav = time.strftime("%Y-%m-%d_%H-%M-%S_%Z", time.localtime())
                logging.info("\n########## \n\nsaving Data to csv with following Parameters: \n Exposure Time: %s \n Gain: %s \n Pixel Format: %s \n Sensor Bit Depth: %s \nImage Processing Parmaters: \n use BitMask: %s \n use Dark: %s \n use Calibration Faktor: %s \n##########\n\n", self.getParam('CAM-EXPT'), self.getParam('CAM-GAIN'), self.getParam('CAM-Pformat'), self.getParam('CAM-SenBitD'), self.getParam('useBitMask'), self.getParam('useDark'), self.getParam('useCalA'))
            elif val == False:
                logging.info("\n########## \n\nsaving Data to csv stopped  \n##########\n\n")
            else:
                false_val = True
       
        elif reason[0:4] == 'LOSS' and reason != 'LOSS': #if an LOSSxx PV exept LOSS itself changed, thats when a limit LOSSxx PV changes
            if val != '':
                PV,limit = reason.split('_')
                self.setParamInfo(PV, {limit : val})
                dirPV = self.getParamInfo(PV)
                #print(reason, 'has changed to', val, 'so has ', PV, 'changed following limit', limit, 'to', dirPV[limit])
            else:
                false_val = True
                
        else:
            status = False #all the other variables are read only
            
        if false_val:
            logging.warning('False value for PV %s to %s', reason, val)
            return False
            
        if status:
            print('write PV', reason, 'to', val)
            logging.info('write PV %s to %s', reason, val)
            self.setParam(reason, val)
            self.updatePVs()
        else:
            logging.info('PV %s is read-only', reason)
                            
        return status
                            
        
    def read(self, reason): #caget or when a PV has scan defined
                            
        if reason == 'LEDA':
            val = [0,0,0,0,0,0,0,
                   0,0,0,0,0,0,0,
                   0,0,0,0,0,0,0]
            i = 0
            for j in LED_all:
                val[i] =  int(GPIO.input(j))
                i += 1
            return val
        
        elif reason[0:4] == 'LED_': #if a LED_xx variable changes
            name,nr = reason.split('_')
            return GPIO.input(LED_all[int(nr)-1])


        elif reason[0:3] == 'CAM' and self.getParam('isConnected') == False:
            #print('Camera is not connected, so any CAM Variable may not correct, first try connect and check is Connected')
            val = self.getParam(reason)
            return val
        
        elif reason == 'CAM-Pformat':
            val = self.camera.PixelFormat.GetValue()
            return Pformat.index(val)
             
        elif reason == 'CAM-SenBitD':
            val = self.camera.BslSensorBitDepth.GetValue()
            #print(val, 'Index SenBitD',SenBitD.index(val))
            return SenBitD.index(val) 
        
        elif reason == 'CAM-acqFR':
            return self.camera.AcquisitionFrameRate.GetValue()
                            
        elif reason == 'CAM-EacqFR':
            return self.camera.AcquisitionFrameRateEnable.GetValue()

        elif reason == 'CAM-FR':
            return self.camera.ResultingFrameRate.GetValue()
        
        elif reason == 'CAM-EXPT':
            return self.camera.ExposureTime.GetValue()
        
        elif reason == 'CAM-GAMMA':
            return self.camera.Gamma.GetValue()
                
        elif reason == 'CAM-GAIN':
            return self.camera.Gain.GetValue()
        
        elif reason == 'CAM-Temp':
            return round(self.camera.DeviceTemperature.GetValue(), 3)
                            
        elif reason == 'CAM-IMAGE' and self.getParam('CAM-isGrabbing') == False:
            self.setParam('CAM-isGrabbing', True)
            self.updatePVs()
            numberOfImagesToGrab = 1
            try:
                self.camera.StartGrabbingMax(numberOfImagesToGrab)
            except:
                return None
            self.grabResult = self.camera.RetrieveResult(1100, pylon.TimeoutHandling_ThrowException)
            img = self.grabResult.Array
                            
            img = self.SliceIMG(img)#Slice it
            if self.getParam('useDark') == True:
                img = img - self.DarkI             
            if self.getParam('useBitMask') == True:
                img = img * self.BitMask #use bitmask
  
            img_paint = f.paint_raster(img, (4,7), show = False)
            img_flip = np.fliplr(img_paint)
            
            self.grabResult.Release()
            self.camera.StopGrabbing()
            
            self.setParam('CAM-isGrabbing', False)
            self.updatePVs()
            return img_flip.flatten()
        
        else:
            val = self.getParam(reason) #get current value
        return val

    
    def StartGrabbing(self):
        self.camera.StartGrabbing(pylon.GrabStrategy_LatestImageOnly)#test other grabStrategies
        wait = True
        while True:
            time.sleep(1) # in sec
            if not self.camera.GetGrabResultWaitObject().Wait(0):
                #print("Wait until a grab result is in the output queue")
                logging.info("StartGrabbing: Wait until a grab result is in the output queue")
            else:
                #print("A grab result waits in the output queue.")
                logging.info("StartGrabbing: A grab result waits in the output queue.")
                break     
                      
    def SliceIMG(self, img):#slice the image with the current slicing parameters
        return img[self.y_start:self.y_end,self.x_start:self.x_end]       
   
    def set_IMAGExy(self):
        self.setParam('CAM-IMAGEx', self.x_end - self.x_start)
        self.setParam('CAM-IMAGEy', self.y_end - self.y_start)
        self.setParam('POS-applied', 0)#it is necessary to apply the new Position to Dark and Bitmask (CAM-applyPOS)
        self.updatePVs()
    
    def default_settings(self):
        self.camera.PixelFormat = "Mono12p"
        #self.camera.ExposureTime =32000
        self.camera.BinningHorizontalMode = "Sum"
        self.camera.BinningVerticalMode = "Sum"
        self.camera.BinningHorizontal = 4
        self.camera.BinningVertical = 4
        self.camera.Width = 480
        self.camera.Height = 300
        self.camera.AcquisitionFrameRate = 100
        self.camera.AcquisitionFrameRateEnable = True
        self.camera.ExposureAuto = "Off"
        self.camera.BslSensorBitDepthMode = 'Manual'
        self.camera.BslSensorBitDepth = 'Bpp12'
        self.camera.Gamma = 1
        self.camera.Gain = 0
        self.camera.DeviceTemperatureSelector = 'Coreboard'
        self.camera.AutoFunctionROIUseBrightness = False
        self.camera.LUTEnable = False
        return None
    
    def loadCdata(self, newPOS=False):
        # try: if file already exist; except: take init values
        
        if not newPOS:
            
            try:
                # Position Parameters
                with open(PATH_Pos+'_last_position.json', 'r') as file:
                    self.pos_json = json.load(file)

            except:
                self.pos_json = {'Time': 'No Position yet', 
                     'Timestamp' : 0,
                     'Slice Parameters(y_start,y_end, x_start, x_end):': (0,300,0,480),
                       }
                
            #Positioning Variables
            self.x_start = self.pos_json['Slice Parameters(y_start,y_end, x_start, x_end):'][2]
            self.x_end = self.pos_json['Slice Parameters(y_start,y_end, x_start, x_end):'][3]
            self.y_start = self.pos_json['Slice Parameters(y_start,y_end, x_start, x_end):'][0]
            self.y_end = self.pos_json['Slice Parameters(y_start,y_end, x_start, x_end):'][1]
            self.set_IMAGExy()    
                
            
        else: #if the new Position comes from GUI one have to write it to the file
            print('new Position from GUI')
            #change json from Bitmask and Dark?
            # save a Dictionary with all the Data to a .json file
            time_txt = time.strftime("%Y-%m-%d_%H-%M-%S_%Z", time.localtime())
            self.pos_json = {'Time': time_txt, 
                     'Timestamp' : time.time(),
                     'Slice Parameters(y_start,y_end, x_start, x_end):': (self.y_start,self.y_end,self.x_start,self.x_end),
                       }
            #print('BitMask_json:', BitMask_json)
            with open(PATH_Pos+'_last_position.json', 'w') as file:
                json.dump(self.pos_json, file)
            #save with Time and Date -> Archiv    
            with open(PATH_Pos + time_txt + '_position.json', 'w') as file:
                json.dump(self.pos_json, file)
        
        try:
            #open Bitmask
            with open(PATH_BM+'_last_bitmask.npy', 'rb') as file:
                self.BitMask = np.load(file) 

            self.BitMask = np.array(self.BitMask, dtype=int)
        except Exception as e:
            #print('Error Bitmask:',e)
            self.BitMask = np.zeros(300*480).reshape(300, 480)
            
        try:
            # open BitMask and Calibration Parameters
            with open(PATH_BM+'_last_BM_Cal_parameters.json', 'r') as file:
                self.BM_Cal_json = json.load(file)
        except:
            # default values, which are PVs
            self.BM_Cal_json = {'Time': 'No Bitmask and Calibration yet', 
                     'Threshhold': 1, 
                     'Exposure Time': 5000, 
                     'Saturation Array': tuple(np.array(np.zeros(splits[0]*splits[1]), dtype='float')),
                     'Channels Array': tuple(np.array(np.zeros(splits[0]*splits[1]),dtype='float')),
                     'LED_Calibration': False, }
                
        #edge BitMask
        self.EdgeBM = np.ones(300*480).reshape(300, 480)
        self.EdgeBM[self.y_start:self.y_end,self.x_start:self.x_end]=0 #simple Edge around regtagle
        self.EdgeBM = ~self.BitMask.astype('bool')*~self.EdgeBM.astype('bool')
        self.EdgeBM = self.EdgeBM.astype('int') #inverses of the BM without the Edge around the regtagle

        self.BitMask = self.SliceIMG(self.BitMask)#Slice it
        self.BitMask_view = f.paint_raster(self.BitMask, (4,7), show = False)
        self.BitMask_view = np.fliplr(self.BitMask_view) #mirror it, that Fiber 1 is in upper left corner

        try:
            #open CalA
            with open(PATH_Cal+'_last_CalA.npy', 'rb') as file:
                self.CalA = np.load(file)
            #print(CalA)
        except:
            self.CalA = np.ones(splits[0]*splits[1]).reshape(splits[0],splits[1])
        try:
            #open last CalI       
            with open(PATH_Cal+'_last_CalI.npy', 'rb') as file:
                self.CalI = np.load(file)
        except:
            self.CalI = np.ones(300*480).reshape(300, 480)
            
        try:
            #open last DarkI       
            with open(PATH_Dark+'_last_DarkI.npy', 'rb') as file:
                self.DarkI = np.load(file)
        except:
            self.DarkI = np.ones(300*480).reshape(300, 480)

        #EdgeLoss0
        try:
            self.EdgeLoss0 = np.average(self.DarkI, weights = self.EdgeBM)
        except:#when weigths sum up to zero
            self.EdgeLoss0 = 1
        logging.info('EdgeLoss0: %s ', self.EdgeLoss0)

        #print('DarkI:', DarkI)
        self.DarkI = self.SliceIMG(self.DarkI)# Slice it

        # Calculate DarkA
        self.DarkA = f.split_sum(self.DarkI, splits)

        #with BitMask
        self.DarkI_BM = self.DarkI*self.BitMask
        self.DarkA_BM = f.split_sum(self.DarkI_BM, splits)

        #with Edge Substraction
        DarkI_E = self.DarkI - self.EdgeLoss0
        self.DarkA_E = f.split_sum(DarkI_E,splits)
         #with Bitmask
        DarkI_E_BM = DarkI_E*self.BitMask 
        self.DarkA_E_BM = f.split_sum(DarkI_E_BM, splits)                           

        try:
            #open Dark parameters
            with open(PATH_Dark+'_last_Dark_parameters.json', 'r') as file:
                self.dark_json = json.load(file)
        except:
            # default values, which are PVs
            self.dark_json = {'Time': 'None Dark yet', 
                             'Exposure Time': 0,}

        #DarkA = np.ones(splits[0]*splits[1]).reshape(splits[0], splits[1])#zeros
        #DarkI = np.zeros(Lx*Ly).reshape(Ly,Lx)
        
        
        #init some PV from loaded data
        self.setParam('CAM-X_START', self.x_start)
        self.setParam('CAM-X_END', self.x_end)
        self.setParam('CAM-Y_START', self.y_start)
        self.setParam('CAM-Y_END', self.y_end)
        self.setParam('POS-applied', True)
        self.setParam('POS-Time', self.pos_json['Time'])
        self.setParam('BitMask', self.BitMask_view.flatten())
        self.setParam('BitMask-TH', int(self.BM_Cal_json['Threshhold']))
        self.setParam('BM_Cal-Time', self.BM_Cal_json['Time'])
        self.setParam('BM_Cal-EXPT', self.BM_Cal_json['Exposure Time'])
        self.setParam('Dark-EXPT', self.dark_json['Exposure Time'])
        self.setParam('Dark-Time',self.dark_json['Time'])
        self.setParam('CalA', self.CalA.flatten())
        self.setParam('CalI', self.CalI.flatten())
        self.setParam('CalA-LED', self.BM_Cal_json['LED_Calibration'])
        self.setParam('EdgeLoss0',self.EdgeLoss0)
        self.setParam('CAM-EXPT', self.dark_json['Exposure Time'])
        for i in range(splits[0]*splits[1]):
            self.setParam('DarkA'+str(i+1), self.DarkA.flat[i])
        for i in range(splits[0]*splits[1]):
            self.setParam('DarkA_BM'+str(i+1),self.DarkA_BM.flat[i])
        for i in range(splits[0]*splits[1]):
            self.setParam('SatA'+str(i+1),self.BM_Cal_json['Saturation Array'][i])
        for i in range(splits[0]*splits[1]):
            self.setParam('ChlA'+str(i+1),self.BM_Cal_json['Channels Array'][i])
        for i in range(splits[0]*splits[1]):
            self.setParam('CalA'+str(i+1),self.CalA.flat[i])
        self.updatePVs()
    
    def measurement(self, NR_img = True):
        self.StartGrabbing()

        i = 0
        t0 = time.time()
        while NR_img:
            t1 = time.time()
            self.grabResult = self.camera.RetrieveResult(5000, pylon.TimeoutHandling_ThrowException) #pylon.TimeoutHandling_Return)
            if self.grabResult.GrabSucceeded():
                # Access the image data.
                img = self.grabResult.Array
                #print(img.shape)
                
                #Camera analysation
                self.setParam('MeanP', np.mean(img))
                #EdgeLoss0
                try:
                    self.EdgeLoss = np.average(DarkI, weights = self.EdgeBM)
                except:#when weigths sum up to zero
                    self.EdgeLoss = 1
                self.setParam('EdgeLoss', self.EdgeLoss)
   
                self.EdgeLossN = self.EdgeLoss/self.EdgeLoss0
                self.setParam('EdgeLossN', self.EdgeLossN)
                         
                #________________Image Interpretation_______as fast as possible______
                # 1) Slice it
                img = img[self.y_start:self.y_end,self.x_start:self.x_end]
                if self.getParam('useEdgeCor')==True:
                    img = img - self.EdgeLoss
                # 2) use BitMask
                if self.getParam('useBitMask') == True:
                    img = img * self.BitMask #use bitmask
                # 3) Analysis
                arr = f.split_sum(img, splits)
                # 4) Subtract Dark Array
                if self.getParam('useDark') == True:
                    if self.getParam('useBitMask') == True:
                        if self.getParam('useEdgeDarkCor') == True:
                            arr = arr - self.DarkA_BM*self.EdgeLossN
                        elif self.getParam('useEdgeCor')==True:
                            arr = arr - self.DarkA_E_BM
                        else:
                            arr = arr - self.DarkA_BM
                    else:
                        if self.getParam('useEdgeDarkCor') == True:
                            arr = arr - self.DarkA*self.EdgeLossN
                        elif self.getParam('useEdgeCor')==True:
                            arr = arr - self.DarkA_E
                        else:
                            arr = arr - self.DarkA
                        
                # 5) Correction with Calibration Faktor Array
                if self.getParam('useCalA') == True:
                    arr = arr/self.CalA #divide
                
                value = arr.flatten()
                par = np.array([int(self.getParam('useBitMask')),int(self.getParam('useDark')),int(self.getParam('useCalA'))])
                sav = np.concatenate((t1, value, par), axis=None)
                sav = np.expand_dims(sav, axis = 0) #to save it on one column in .csv
                
                #save to csv File
                if self.getParam('save') == True:
                    if not os.path.exists('../Data/EPICS_GUI/'+self.time_sav+'_Data.csv'):#when file doesn't exist, first time
                          with open(PATH_sav+self.time_sav+'_Data.csv', 'wb') as file:
                                LABEL = ["Timestamp"]
                                for i in range(splits[0]*splits[1]):
                                    LABEL.append("LOSS"+ str(i+1))
                                LABEL.extend(["Bitmask "+str(self.getParam('BM_Cal-Time')), "Dark "+str(self.getParam('Dark-Time')), "Calibration Faktor "+str(self.getParam('BM_Cal-Time'))])   
                                #print(LABEL, len(LABEL))
                                np.savetxt(file, [LABEL], delimiter = ',', fmt = '%s')      
                                
                    with open(os.path.join(CWD,'../Data/EPICS_GUI/'+self.time_sav+'_Data.csv'), 'ab') as file:
                        np.savetxt(file, sav,delimiter = ',')

                #save to LOSS variables
                self.setParam('LOSS', sav)
                for j in range(splits[0]*splits[1]):
                    self.setParam('LOSS'+str(j+1), value[j])
                self.updatePVs()
       
                #global stop_measurement
                if self.getParam('CAM-isGrabbing') == False:
                    self.grabResult.Release()
                    self.camera.StopGrabbing()
                    sav = np.zeros(splits[0]*splits[1]+1)
                    sav[:]=-1
                    self.setParam('LOSS', sav)#reset the LOSS Variabels to -1
                    
                    for j in range(splits[0]*splits[1]):
                        self.setParam('LOSS'+str(j+1), -1)
                        self.updatePVs()
                    break
                
                elif self.getParam('CAM-acqDark') == True:
                    self.grabResult.Release()
                    self.setParam('CAM-isGrabbing', False)
                    self.updatePV('CAM-isGrabbing')
                    time.sleep(0.1)
                    print('pause measure function, CAM-isGrabbing:', self.getParam('CAM-isGrabbing'))
                    #wait until Dark is finished
                    while self.getParam('CAM-acqDark') == True:
                        time.sleep(1)
                        print('measuring waits for dark to be finished')
                    print('waiting finished')
                t2 = time.time()
                tdiff = t2-t1
            
                self.setParam('Meas-time', tdiff*1000000) #time for the process of one Measurement
                self.updatePVs()
                time.sleep(self.getParam('Meas-delay')) # in sec


    def acq_BM_Cal(self, j=100):
        
        expt0 = self.getParam('CAM-EXPT') #get current exposure Time
        self.write('CAM-EXPT',self.read('BM_Cal-EXPT')) #set to value for BitMask and Calibration
        self.write('LEDall', 0) #LED off
        
        """ 
        while True:
            time.sleep(1)
            if self.camera.ExposureTime.GetValue() == self.getParam('BM_Cal-EXPT') and self.getParam('LEDall') == 0: #check expt and LED
                print('BM Cal EXPT and LEDall set successfully')
                break
            else:
                print('ERROR: BM Cal Expt not set')
         """   
            
        #acq Dark with LED off
        self.StartGrabbing()
        width = self.getParam('CAM-WIDTH')
        height = self.getParam('CAM-HEIGHT')
        Isum = np.zeros(width*height).reshape(height, width)
        for i in range(j):
            self.write('BM_Cal-NR', i+1) #counter :)
            time.sleep(0.05)
            self.grabResult = self.camera.RetrieveResult(5000,pylon.TimeoutHandling_Return)
            if self.grabResult.GrabSucceeded():
                img = self.grabResult.Array
                # sum it up
                Isum += img                    
        DarkI = Isum/j
        self.grabResult.Release()
                            
        
        DarkIs = self.SliceIMG(DarkI) # Slice it
        #Calculate DarkA with BitMask
        DarkI_BM = DarkIs*self.BitMask
        DarkA_BM = f.split_sum(DarkI_BM, splits)
        print('DarkA_BM from acqCal \n', DarkA_BM)
        
        self.write('LEDall', 1) #LED off
        if self.getParam('LEDall') == 1: #check LED
            print('BM Cal LED set successfully on')
        else:
            print('ERROR: BM Cal LED not set on')
            
        #,acq Flatfield and BitMask with LED on
        Isum = np.zeros(width*height).reshape(height, width)
        for i in range(j):
            self.write('BM_Cal-NR', i+101) #counter :)
            time.sleep(0.05)
            self.grabResult = self.camera.RetrieveResult(5000,pylon.TimeoutHandling_Return)
            if self.grabResult.GrabSucceeded():
                img = self.grabResult.Array
                # sum it up
                Isum += img                    
        CalI = Isum/j
        self.grabResult.Release()
        
        self.camera.StopGrabbing()
        
        #calculate Bitmask
        threshhold = self.getParam('BitMask-TH')
        ret, mask = cv.threshold(CalI, threshhold, 1, cv.THRESH_BINARY)#ret = treshhold
        mask = np.array(mask, dtype=int) #whole image
                            
        self.BitMask = self.SliceIMG(mask) #Slice it
        self.BitMask_view = f.paint_raster(self.BitMask, (4,7), show = False)
        self.BitMask_view = np.fliplr(self.BitMask_view)
        
        #calculate Saturation
        arr = f.split_sum(self.BitMask, splits)
        val = arr.flatten()*4095 #Max Brigthness (NR. Pixels * Mono12)
        
        #calculate new DarkA_BM
        self.DarkI_BM = self.DarkI*self.BitMask
        self.DarkA_BM = f.split_sum(self.DarkI_BM, splits)
        
        #find out which channel is connected
        self.ChlA = np.zeros(splits[0]*splits[1]).reshape(splits[0],splits[1])
        for i in range(splits[0]*splits[1]):
            if val[i] != 0: #CalA.flat[i] > DarkA_BM.flat[i]: #not connected channels should be zero because of the BitMask
                self.ChlA.flat[i] = 1 #channel is connected
        print('Connected channels \n', self.ChlA)       
                            
        #calculate CalA
        CalI = CalI-DarkI #DarkI correction
        self.CalI = self.SliceIMG(CalI) # Slice it
        self.CalI = self.CalI*self.BitMask # with BitMask
        CalA = f.split_sum(self.CalI, splits) #Calculate CalA
        print('CalA with subtracted dark and Bitmask \n', CalA)
        self.CalA = f.norm_A(CalA, self.ChlA) #CalA normalize connected channels whitout LED Calibration
        print('CalA: \n', self.CalA)
        
        
        #save DarkI for Flatfield
        time_txt = time.strftime("%Y-%m-%d_%H-%M-%S_%Z", time.localtime())
        expt_ms = str(self.getParam('CAM-EXPT')/1000) + 'ms'
            #save with Time and Date -> Archiv
        with open(PATH_Cal + time_txt + '_DarkI_' + expt_ms + '.npy', 'wb') as file:
            np.save(file, DarkI)
            #save as _last_ for reopening
        with open(PATH_Cal+'_last_DarkI.npy', 'wb') as file:
            np.save(file, DarkI)
                                  
        #save CalI
            #save with Time and Date -> Archiv
        with open(PATH_Cal + time_txt + '_CalI_' + expt_ms + '.npy', 'wb') as file:
            np.save(file, CalI)
            #save as _last_ for reopening
        with open(PATH_Cal+'_last_CalI.npy', 'wb') as file:
            np.save(file, CalI)
            
        #save CalA
            #save with Time and Date -> Archiv
        with open(PATH_Cal + time_txt + '_CalA_' + expt_ms + '.npy', 'wb') as file:
            np.save(file, self.CalA)
            #save as _last_ for reopening
        with open(PATH_Cal+'_last_CalA.npy', 'wb') as file:
            np.save(file, self.CalA)
        
        #save Bitmask
            #save with Time and Date -> Archiv 
        with open(PATH_BM + time_txt + '_bitmask_' + expt_ms + '.npy', 'wb') as file:
            np.save(file, mask)
            #save as _last_ for reopening
        with open(PATH_BM+'_last_bitmask.npy', 'wb') as file:
            np.save(file, mask)
        
        # save a Dictionary with all the Data to a .json file
        self.BM_Cal_json = {'Time': time_txt, 
                     'Timestamp' : time.time(),
                     'Threshhold': self.getParam('BitMask-TH'), 
                     'Exposure Time': self.getParam('CAM-EXPT'), 
                     'Sensor Bit Depth': self.getParam('CAM-SenBitD'), 
                     'Pixelformat': self.getParam('CAM-Pformat'), 
                     'Gain': self.getParam('CAM-GAIN'),
                     'Img Size': (self.getParam('CAM-HEIGHT'), self.getParam('CAM-WIDTH')),
                     'Slice Parameters(y_start,y_end, x_start, x_end):': (self.y_start,self.y_end,self.x_start,self.x_end),
                     'Saturation Array': tuple(np.array(val, dtype='float')),
                     'Channels Array': tuple(np.array(self.ChlA.flatten(),dtype='float')),
                     'Calibration Array': tuple(np.array(self.CalA.flatten(), dtype='float')),
                     'LED_Calibration': self.getParam('CalA-LED'),
                     'Shape of Arrays': tuple(np.array(CalA.shape, dtype='float')),}
        #print('BM_Cal_json:', BM_Cal_json)        
            #save with Time and Date -> Archiv    
        with open(PATH_BM + time_txt + '_BM_Cal_' + expt_ms + '.json', 'w') as file:
            json.dump(self.BM_Cal_json, file)
            #save as _last_ for reopening
        with open(PATH_BM+'_last_BM_Cal_parameters.json', 'w') as file:
            json.dump(self.BM_Cal_json, file)
        
        
        for j in range(splits[0]*splits[1]):
            self.setParam('DarkA_BM'+str(j+1), self.DarkA_BM.flatten()[j])        
        #print('Saturation', val)
        self.setParam('SatA', val)  
        for j in range(splits[0]*splits[1]):
                    self.setParam('SatA'+str(j+1), val[j])
        for j in range(splits[0]*splits[1]):
            self.setParam('CalA'+str(j+1), self.CalA.flatten()[j])
        self.setParam('CalA', self.CalA.flatten())
        for i in range(splits[0]*splits[1]):
            self.setParam('ChlA'+str(i+1), self.ChlA.flat[i])
        self.setParam('CalI', self.CalI.flatten())
        self.setParam('BM_Cal-EXPT', int(self.getParam('CAM-EXPT')))
        self.write('CAM-EXPT', expt0)
        self.write('LEDall', 0) #LED off
        self.setParam('CalA-LED', False)
        self.setParam('BitMask', self.BitMask_view.flatten())
        self.setParam('BM_Cal-Time', time_txt)
        self.setParam('CAM-acq_BM_Cal', False) #resets the value
        self.setParam('CAM-isGrabbing', False)#resets the isGrabbing state of Camera
        self.updatePVs()
        
        #print('acq_BM_Cal finished')
        logging.info('acqBM_Cal finished')
        return None #end of Function

    
    def acqDark(self, j=100):
        while self.getParam('CAM-isGrabbing') == True:
                time.sleep(0.4)
                #print('cannot acq Dark, must wait until CAM-isGrabbing == False, current', self.getParam('CAM-isGrabbing'))
        if self.getParam('CAM-measure') == False:#if measuring hasn't started
            self.StartGrabbing()
            notM = True
        else:
            notM = False
            
        self.setParam('CAM-isGrabbing', True)
        self.updatePVs()
        print('now can start CAM-isGrabbing True for Dark')
            
            
        grab = True
        while grab == True:
            time.sleep(0.1)
            try: 
                self.grabResult.Array
                print('cannot acq Dark, must wait until grabResult.Release')
            except:
                print('can start new grab,free grabResult')
                break
        
        
        width = self.getParam('CAM-WIDTH')
        height = self.getParam('CAM-HEIGHT')
        DarkIsum = np.zeros(width*height).reshape(height, width)
        for i in range(j):
            self.write('Dark-NR', i+1) #counter :)
            self.grabResult = self.camera.RetrieveResult(5000,pylon.TimeoutHandling_Return)
            if self.grabResult.GrabSucceeded():
                img = self.grabResult.Array
                # sum it up
                DarkIsum += img                    
        DarkI = DarkIsum/j
        self.grabResult.Release() #after release grabResult.Array,grabResult.ID = error Nullpointer
        
        #EdgeLoss0
        try:
            self.EdgeLoss0 = np.average(DarkI, weights = self.EdgeBM)
        except:#when weigths sum up to zero
            self.EdgeLoss0 = 1
        self.setParam('EdgeLoss0', self.EdgeLoss0)
                            
        # Slice it
        self.DarkI= self.SliceIMG(DarkI)
        
        # Calculate DarkA
        self.DarkA = f.split_sum(self.DarkI, splits)
            #with BitMask
        self.DarkI_BM = self.DarkI*self.BitMask
        self.DarkA_BM = f.split_sum(self.DarkI_BM, splits)
                         
        #with Edge Substraction
        self.DarkI_E = self.DarkI - self.EdgeLoss0
        self.DarkA_E = f.split_sum(self.DarkI_E,splits)
            #with Bitmask
        self.DarkI_E_BM = self.DarkI_E*self.BitMask 
        self.DarkA_E_BM = f.split_sum(self.DarkI_E_BM, splits)
                           
        #save DarkI
        time_txt = time.strftime("%Y-%m-%d_%H-%M-%S_%Z", time.localtime())
        expt_ms = str(self.getParam('CAM-EXPT')/1000) + 'ms'
            #save with Time and Date -> Archiv
        with open(PATH_Dark + time_txt + '_DarkI_' + expt_ms + '.npy', 'wb') as file:
            np.save(file, DarkI)
            #save as _last_ for reopening
        with open(PATH_Dark+'_last_DarkI.npy', 'wb') as file:
            np.save(file, DarkI)

        # save a Dictionary with all the Data to a .json file
        dark_json = {'Time': time_txt, 
                     'Timestamp' : time.time(),
                     #'BitMask': self.getParam('useBitMask') , 
                     'Exposure Time': self.getParam('CAM-EXPT'), 
                     'Sensor Bit Depth': self.getParam('CAM-SenBitD'), 
                     'Pixelformat': self.getParam('CAM-Pformat'), 
                     'Gain': self.getParam('CAM-GAIN'),
                     'Img Size': (self.getParam('CAM-HEIGHT'), self.getParam('CAM-WIDTH')),
                     'Slice Parameters(y_start,y_end, x_start, x_end):': (self.y_start,self.y_end,self.x_start,self.x_end)}
        with open(PATH_Dark+'_last_Dark_parameters.json', 'w') as file:
            json.dump(dark_json, file)
        with open(PATH_Dark + time_txt + '_Dark_parameters.json', 'w') as file:
            json.dump(dark_json, file)
                            
        #set DarkA and DarkA_BM
        for j in range(splits[0]*splits[1]):
            self.setParam('DarkA'+str(j+1), self.DarkA.flatten()[j])
        for j in range(splits[0]*splits[1]):
            self.setParam('DarkA_BM'+str(j+1), self.DarkA_BM.flatten()[j])
                            
        self.setParam('DarkI', self.DarkI.flatten())
        self.setParam('Dark-EXPT', int(self.getParam('CAM-EXPT')))
        self.setParam('Dark-Time', time_txt)
        self.setParam('CAM-acqDark', False)
        if notM:#if measuring hasn't started
            self.camera.StopGrabbing()
            self.setParam('CAM-isGrabbing', False)#resets the isGrabbing state of Camera
        #else: CAM-isGrabbing still True for continuing Measurement
        self.updatePVs()
        
        #print('acqDarkA finished')
        logging.info('acqDark finished')
        return None #end of function
    
    def acq_LEDCal(self, j=100):

        expt0 = self.getParam('CAM-EXPT') #get current exposure Time
        self.write('CAM-EXPT',self.read('LEDCal-EXPT')) #set to value for BitMask and Calibration
        self.write('LEDall', 0) #LED off
        
        #acq Dark with LED off
        self.StartGrabbing()
        width = self.getParam('CAM-WIDTH')
        height = self.getParam('CAM-HEIGHT')
        print('LED Calibration ready for Dark')
        Isum = np.zeros(width*height).reshape(height, width)
        print('LED Calibration ready for Dark2')
        for i in range(j):
            time.sleep(0.05)
            self.grabResult = self.camera.RetrieveResult(5000,pylon.TimeoutHandling_Return)
            if self.grabResult.GrabSucceeded():
                img = self.grabResult.Array
                # sum it up
                Isum += img                    
        DarkI = Isum/j
        self.grabResult.Release()
        print('LED Calibration Dark2 finished')
        DarkIs = self.SliceIMG(DarkI) # Slice it
        #Calculate DarkA with BitMask
        DarkI_BM = DarkIs*self.BitMask
        DarkA_BM = f.split_sum(DarkI_BM, splits)
        print('DarkA_BM from acqCal \n', DarkA_BM)
        
        #save DarkI for LED Calibration
        time_txt = time.strftime("%Y-%m-%d_%H-%M-%S_%Z", time.localtime())
        expt_ms = str(self.getParam('CAM-EXPT')/1000) + 'ms'
            #save with Time and Date -> Archiv
        with open(PATH_LEDCal + time_txt + '_DarkI_' + expt_ms + '.npy', 'wb') as file:
            np.save(file, DarkI)
            #save as _last_ for reopening
        with open(PATH_LEDCal+'_last_DarkI.npy', 'wb') as file:
            np.save(file, DarkI)
            
            
            
        #init some Values
        LEDCalI = np.zeros(width*height).reshape(height, width)
        LEDCalI = self.SliceIMG(LEDCalI)
        LEDCalI[:,:] = 2000 #grey
        LEDCalA = np.zeros(splits[0]*splits[1]).reshape(splits[0], splits[1])
        
        #acq Flatfields for each LED
        for i in range(splits[0]*splits[1]):
            self.setParam('LEDCal-NR', i+1)
            PATH_LED = os.path.join(PATH_LEDCal, '/LED_' + str(i+1))
            f.newdir(PATH_LED)
            #connect LED to channel...
            
            while self.getParam('LEDCal-Next') == 0:
                #wait until Calbration Cable is connected
                time.sleep(0.5)
                print('wait until next LED is connected')
            
            led = np.zeros(21)
            if self.getParam('LEDCal-NR')>21:
                led[i-7] = 1
            else:
                led[i] = 1
            
            self.write('LEDA', led) #one LED on
            if self.getParam('LEDA')[i] == 1: #check LED
                print('LED Cal LED set successfully on')
            else:
                print('ERROR: BM Cal LED not set on')
                
            #acq Flatfield with one LED on
            Isum = np.zeros(width*height).reshape(height, width)
            for i in range(j):
                time.sleep(0.05)
                self.grabResult = self.camera.RetrieveResult(5000,pylon.TimeoutHandling_Return)
                if self.grabResult.GrabSucceeded():
                    img = self.grabResult.Array
                    # sum it up
                    Isum += img                    
            Isum = Isum/j
            self.grabResult.Release()
            
            #save LEDxxCalI
            with open(PATH_LED +'CalI_' + expt_ms + '.npy', 'wb') as file:
                np.save(file, Isum)                        
            
            #calculate LEDxxA
            Isum = Isum-DarkI #DarkI correction
            Isum = self.SliceIMG(Isum) # Slice it
            #Isum = Isum*self.BitMask # with BitMask
            LEDxxA = f.split_sum(Isum, splits) #Calculate CalA
            print('LEDCalA with subtracted dark and Bitmask \n', LEDxxA)
                                    
            #save LEDxxCalA
            with open(PATH_LED + 'CalA_' + expt_ms + '.npy', 'wb') as file:
                np.save(file, LEDxxA)
           
           #update LEDCalA and LEDCalI
            LEDCalA.flat[i] = LEDxxA.flat[i]
            y, x = splits
            ly = np.shape(LEDCalI)[0]//y
            lx = np.shape(LEDCalI)[1]//x
            LEDCalI[i//x*ly:i//x*ly+ly, i%x*lx:i%x*lx+lx] = Isum[i//x*ly:i//x*ly+ly, i%x*lx:i%x*lx+lx]
           
            #calculate LEDFAKTOR
            self.LEDFAKTOR = f.norm_A(LEDCalA, channels=np.array(CalA > 0, dtype=int)) #CalA normalize the already measured LEDs
            print('LEDCalA: \n', LEDCalA)
                                    
            #update PVs
            self.setParam('LEDCalI', LEDCalI.flat)                         
            for i in range(splits[0]*splits[1]):
                self.setParam('LEDFAKTOR'+str(i+1), self.LEDFAKTOR.flat[i])
            for i in range(splits[0]*splits[1]):
                self.setParam('LEDCalA'+str(i+1), LEDCalA.flat[i])                       
            self.setParam('LEDCal-Next', 0)
            self.updatePVs()
            
                                    
                                    

        self.camera.StopGrabbing()
        
                                  
        #save LEDCalI
            #save with Time and Date -> Archiv
        with open(PATH_LEDCal + time_txt + '_LEDCalI_' + expt_ms + '.npy', 'wb') as file:
            np.save(file, LEDCalI)    
        #save LEDCalA
            #save with Time and Date -> Archiv
        with open(PATH_LEDCal + time_txt + '_LEDCalA_' + expt_ms + '.npy', 'wb') as file:
            np.save(file, LEDCalA)
   
        #save LEDFAKTOR
        with open(PATH_LEDCal + time_txt + '_LED-FAKTOR_' + expt_ms + '.npy', 'wb') as file:
            np.save(file, LEDFAKTOR)
            #save as _last_ for reopening
        with open(PATH_LEDCal+'_last_LED-FAKTOR.npy', 'wb') as file:
            np.save(file, self.LEDFAKTOR)                            
                                    
        
        
        # save a Dictionary with all the Data to a .json file
        self.LEDCal_json = {'Time': time_txt, 
                     'Timestamp' : time.time(),
                     'BitMask': '', 
                     'Exposure Time': self.getParam('CAM-EXPT'), 
                     'Sensor Bit Depth': self.getParam('CAM-SenBitD'), 
                     'Pixelformat': self.getParam('CAM-Pformat'), 
                     'Gain': self.getParam('CAM-GAIN'),
                     'Img Size': (self.getParam('CAM-HEIGHT'), self.getParam('CAM-WIDTH')),
                     'Slice Parameters(y_start,y_end, x_start, x_end):': (self.y_start,self.y_end,self.x_start,self.x_end),
                     'LED_Calibration': '',
                     'Shape of Arrays': tuple(np.array(CalA.shape, dtype='float')),}
        #print('BM_Cal_json:', BM_Cal_json)        
            #save with Time and Date -> Archiv    
        with open(PATH_LEDCal + time_txt + '_BM_Cal_' + expt_ms + '.json', 'w') as file:
            json.dump(self.LEDCal_json, file)
            #save as _last_ for reopening
        with open(PATH_BM_LEDCal+'_last_BM_Cal_parameters.json', 'w') as file:
            json.dump(self.LEDCal_json, file)
        
        self.setParam('LEDCal-NR', 0)
        self.setParam('LEDCal-EXPT', int(self.getParam('CAM-EXPT')))
        self.write('CAM-EXPT', expt0)
        self.write('LEDall', 0) #LED off 
        self.setParam('LEDCal-Time', time_txt)
        self.setParam('CAM-acq_LEDCal', False) #resets the value
        self.setParam('CAM-isGrabbing', False)#resets the isGrabbing state of Camera
        self.updatePVs()
        
        #print('acq_BM_Cal finished')
        logging.info('acq_LEDCal finished')
        return None #end of Function
        
    

if __name__ == '__main__': 
    server = SimpleServer()
    server.createPV(prefix, pvdb) #create PVs based on prefix and pvdb definition
    driver = iocDriver()
    while True:
        server.process(0.01) # process CA transactions
        
# cleanup
GPIO.cleanup() # all pins
