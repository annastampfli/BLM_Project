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


#____________________Parameters_____________________


#Camera
Pformat = ['Mono8', 'Mono12', 'Mono12p']
SenBitD = ['Bpp8', 'Bpp10', 'Bpp12']
PVlimits = ['lolo', 'low', 'high', 'hihi']

#_____________________________________________________

#get the Hostname to change the EPICS previx
com = subprocess.Popen(["hostname"], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
output, errors = com.communicate()
com.wait()
print(errors)#logger?
BLM_NR = output[-3:-1]

CWD = os.getcwd()
print(CWD)
#CWD = '/home/slsop/BLM/Program'#future working directory


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
                  'count' : 22,
                  'scan' : 1, #for reloading in the GUI
                  'value' : [0,0,0,0,0,0,0,
                              0,0,0,0,0,0,0,
                              0,0,0,0,0,
                              0,0,0],
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
                  'value' : 0,
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
    'CAM-isMeasuring' : {'type' : 'int', #usage like boolean
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
                   'scan' : 1, 
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
              'value' : 0,
              'count' : splits[0]*splits[1]+1,
             },

    
    'CAM-acqBitMask' : {
        'type' : 'int', #usage as boolean
        'value' : 0,  
        'scan' : 1,
    },
    'BitMask' : {
        'type' : 'int', #usage as boolean array
        'count' : Lx*Ly,#300*480,
#        'value' : BitMask_view.flatten(),
        'scan' : 10 #to display it even when GUI is reloaded
    },
    'useBitMask': {
        'type' : 'int', #usage as boolean
        'value' : 0,
    },
    'BitMask-TH' : { #Bitmask threshhold
        'type' : 'int',
#        'value' : BitMask_json['Threshhold'],
    },
    'BitMask-Time' : {
        'type' : 'string',
#        'value' :  BitMask_json['Time'],
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
#               'value' : DarkI.flatten(),
               'scan' : 10 #to display it even when GUI is reloaded
    },
    'Dark-EXPT' : {
        'type' : 'int',    
        'unit' : 'us',
#        'value' : dark_json['Exposure Time'],
    },
    'Dark-Time' : {
        'type' : 'string',
#       'value' :  dark_json['Time'],
    },
    'useDark': {
        'type' : 'int', #usage as boolean
        'value' : 0,
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

    'SatA' : {
        'type' : 'int', 
        'count' : splits[0]*splits[1], #28
#        'value' : BitMask_json['Saturation Array'],#np.ones(splits[0]*splits[1]),
        'scan' : 1,
    },
    'useSat': { #use Saturation
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
for i in range(14):
    LEDdir['LED_'+str(i+1)] = {'type' : 'int', #usage like boolean
                              'value' : 0,
                              'scan' : 1, #execute the read function reguarly
                             }

LOSSdir = {}    
for i in range(splits[0]*splits[1]):
    LOSSdir['LOSS'+str(i+1)] = {'type' : 'float',
                                'prec' : 1,
                                'value' : 0,
                                'low' : -100, 'high' : 100, #Data limit for low / high alarm, -> Warning
                                'lolo' : -200, 'hihi' : 1000000, #Data limit for low low / high high alarm, -> Alarm
                             'lolim' : -200, 'hilim' : 13304655, #Data limit for graphics Display, complete Saturation for ROI 57x57=3249Pix Mono12
                               }
    for limit in PVlimits:
        LOSSdir['LOSS'+str(i+1)+'_'+limit] = {} #create LOSS1_high PV...
    
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

pvdb.update(LEDdir)  # To add two dictionary  
pvdb.update(LOSSdir) 
pvdb.update(DarkAdir)
pvdb.update(DarkA_BMdir)
pvdb.update(SatAdir)


class iocDriver(Driver):

    def __init__(self):
        super(iocDriver, self).__init__()
        print('__init__ function started')
    
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
                
        
        
    def loadCdata(self, newPOS=False):
        # try: if file already exist; except: take init values
            
            
        if not newPOS:
            
            try:
                # Position Parameters
                with open(os.path.join(CWD,'../Calibration_Data/Position/_last_position.json'), 'r') as file:
                    self.pos_json = json.load(file)
                #print(self.BitMask_json)

            except:
                print('this is default Position')
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
            with open(os.path.join(CWD,'../Calibration_Data/Position/_last_position.json'), 'w') as file:
                json.dump(self.pos_json, file)
            #save with Time and Date -> Archiv    
            with open(os.path.join(CWD,'../Calibration_Data/Position/' + time_txt + '_position.json'), 'w') as file:
                json.dump(self.pos_json, file)
            
        print('Slice Parameters',self.x_start, self.x_end, self.y_start, self.y_end)
        
        
        try:
            #open Bitmask
            with open(os.path.join(CWD,'../Calibration_Data/BitMask/_last_bitmask.npy'), 'rb') as file:
                self.BitMask = np.load(file) 

            self.BitMask = np.array(self.BitMask, dtype=int)
        except:
            self.BitMask = np.zeros(300*480).reshape(300, 480)
            
        try:
                # BitMask Parameters (BitMask-Time, BitMask-TH)
                with open(os.path.join(CWD,'../Calibration_Data/BitMask/_last_bitmask_parameters.json'), 'r') as file:
                    self.BitMask_json = json.load(file)
                #print(self.BitMask_json)

        except:
            print('this is default BitMask')
            self.BitMask_json = {'Time': 'None BitMask yet',
                                 'Timestamp' : 0,
                                 'Threshhold': 0,
                                 'Exposure Time': 0, 
                                 'Sensor Bit Depth':0,
                                 'Pixelformat': 0, 
                                 'Gain': 0,
                                 'Img Size': (300,480),
                                 'Slice Parameters(y_start,y_end, x_start, x_end):': (0,300,0,480),
                                 'Saturation Array': tuple(np.array(np.zeros(28), dtype=float))}
                
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
            CalA_Version = 'FAKTOR_V3_SQRT.npy'
            with open(os.path.join(CWD,'../Calibration_Data/'+CalA_Version), 'rb') as file:
                self.CalA = np.load(file)
            #print(CalA)
        except:
            self.CalA = np.ones(splits[0]*splits[1]).reshape(splits[0],splits[1])

        try:
            #open last DarkI       
            with open(os.path.join(CWD,'../Calibration_Data/Dark/_last_DarkI.npy'), 'rb') as file:
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
            # Dark Parameters (Dark-EXPT, Dark-Time, Dark-useBitMask)
            with open(os.path.join(CWD,'../Calibration_Data/Dark/_last_Dark_parameters.json'), 'r') as file:
                self.dark_json = json.load(file)
            #print(dark_json)
        except:
            self.dark_json = {'Time': 'None Dark yet', 
                             'Timestamp' : 0,
                             #'BitMask': self.getParam('useBitMask') , 
                             'Exposure Time': 0, 
                             'Sensor Bit Depth': 0, 
                             'Pixelformat': 0, 
                             'Gain': 0,
                             'Img Size': 0,
                             'Slice Parameters(y_start,y_end, x_start, x_end):': (0,300,0,480)}

        #DarkA = np.ones(splits[0]*splits[1]).reshape(splits[0], splits[1])#zeros
        #DarkI = np.zeros(Lx*Ly).reshape(Ly,Lx)
        
        
        #init some PV
        self.setParam('CAM-X_START', self.x_start)
        self.setParam('CAM-X_END', self.x_end)
        self.setParam('CAM-Y_START', self.y_start)
        self.setParam('CAM-Y_END', self.y_end)
        self.setParam('POS-applied', True)
        self.setParam('POS-Time', self.pos_json['Time'])
        self.setParam('BitMask', self.BitMask_view.flatten())
        self.setParam('BitMask-TH', self.BitMask_json['Threshhold'])
        self.setParam('BitMask-Time', self.BitMask_json['Time'])
        self.setParam('Dark-EXPT', self.dark_json['Exposure Time'])
        self.setParam('Dark-Time',self.dark_json['Time'])
        self.setParam('CalA', self.CalA.flatten())
        self.setParam('EdgeLoss0',self.EdgeLoss0)
        for i in range(splits[0]*splits[1]):
            self.setParam('DarkA'+str(i+1), self.DarkA.flatten()[i])
        for i in range(splits[0]*splits[1]):
            self.setParam('DarkA_BM'+str(i+1),self.DarkA_BM.flatten()[i])
        for i in range(splits[0]*splits[1]):
            self.setParam('SatA'+str(i+1),self.BitMask_json['Saturation Array'][i])
        self.updatePVs()


   
    def set_IMAGExy(self):
        self.setParam('CAM-IMAGEx', self.x_end - self.x_start)
        self.setParam('CAM-IMAGEy', self.y_end - self.y_start)
        self.setParam('POS-applied', 0)#it is necessary to apply the new Position to Dark and Bitmask (CAM-applyPOS)
        self.updatePVs()
        
        
                
                
    def write(self, reason, val): #caput
        status = True #determines if the value is written to thterminate called after throwing an instance of 'Swig::DirectorMethodException'
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
                self.updatePVs()
           
            elif val == False:
                GPIO.output(LED_all, GPIO.LOW)
                self.updatePVs()
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
                except:
                    #print('An Error with connection occured')
                    logging.error('could not connect to the camera')
                    return False
                #print("Using device: ", self.camera.GetDeviceInfo().GetModelName())
                logging.info('*** Using device: %s ***' , self.camera.GetDeviceInfo().GetModelName())
            elif val == False:
                if self.getParam('CAM-isMeasuring') == True:
                    self.setParam('CAM-measure', False)# code from CAM-measure == False
                    self.setParam('CAM-isMeasuring', False)
                    self.updatePVs()
                    self.CAM_thread.join() #really waits until the thread measurement is finished
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
            if self.getParam('CAM-isMeasuring') == False and self.getParam('isConnected'):
                #print(val, Pformat[val])
                self.camera.PixelFormat = Pformat[val]
            else:
                logging.warning('can not change PV %s when Camera is measuring', reason)
                #print('can not change when Camera not connected or measuring.')
                
        elif reason == 'CAM-SenBitD': # can only be changed, when camera not measuring
            if self.getParam('CAM-isMeasuring') == False and self.getParam('isConnected'):
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
            if val == True and self.getParam('CAM-isMeasuring') == False:
                # Camera Measurement Thread
                self.CAM_thread = threading.Thread(target = self.measurement, daemon = True)
                self.setParam('CAM-isMeasuring', True)
                self.updatePVs()
                self.CAM_thread.start()
                logging.info("\n______________________________________________________\n\nCamera started measuring with following Parameters: \n Exposure Time: %s \n Gain: %s \n Pixel Format: %s \n Sensor Bit Depth: %s \nImage Processing Parmaters: \n use BitMask: %s \n use Dark: %s \n use Calibration Faktor: %s \n______________________________________________________\n", self.getParam('CAM-EXPT'), self.getParam('CAM-GAIN'), self.getParam('CAM-Pformat'), self.getParam('CAM-SenBitD'), self.getParam('useBitMask'), self.getParam('useDark'), self.getParam('useCalA'))
            elif val == False and self.getParam('CAM-isMeasuring') == True:
                self.setParam('CAM-isMeasuring', False)
                self.updatePVs()
                self.CAM_thread.join() #really waits until the thread is finished
                logging.info("\n______________________________________________________\n\nCamera stopped measuring \n______________________________________________________\n")
            else:
                false_val = True
        
        elif reason == 'CAM-acqBitMask': # can only be changed, when camera not measuring
            if val == True and self.getParam('CAM-isMeasuring') == False:
                status = True #writes the PV -> sets the value to True
                #acquire BitMask Thread
                self.BitMask_thread = threading.Thread(target = self.acqBitMask, daemon = True)
                self.setParam('CAM-isMeasuring', True)
                self.updatePVs()
                self.BitMask_thread.start()     
            else:
                logging.warning('can not acquire BitMask, when Camara is measuring.')
                #print('can not acquire BitMask when Camera not connected or measuring.') 
                return False
                
        elif reason == 'CAM-acqDark': # can only be changed, when camera not measuring
            if val == True and self.getParam('CAM-isMeasuring') == False:
                status = True #writes the PV -> sets the value to True
                self.setParam('CAM-isMeasuring', True)
                self.updatePVs()
                # acquire Dark Thread
                self.Dark_thread = threading.Thread(target = self.acqDark, daemon = True)
                self.Dark_thread.start()     
            else:
                logging.warning('can not acquire Dark, when Camara is measuring.')
                #print('can not acquire Dark when Camera not connected or measuring.') 
                return False
                
        elif reason == 'useBitMask':
            if val == True or val == False:
                status = True
            else:
                false_val = True
                
        elif reason == 'BitMask-TH':
            if 0 <= val <= 4095: #12bit
                status = True
            else: 
                 false_val = True
       
        elif reason == 'CAM-X_START':
            self.x_start = val
            self.set_IMAGExy()
            status = True
            
        elif reason == 'CAM-X_END':
            self.x_end = val
            self.set_IMAGExy()
            status = True
            
        elif reason == 'CAM-Y_START':
            self.y_start = val
            self.set_IMAGExy()
            status = True
        
        elif reason == 'CAM-Y_END':
            self.y_end = val
            self.set_IMAGExy()
            status = True
            
        elif reason == 'CAM-applyPOS':
            if val == True:
                #calculates new sliced Dark, sliced Bitmasks, Edgelosses on base of current Data
                self.setParam('CAM-applyPOS', 1)
                self.updatePVs()
                self.loadCdata(newPOS=True)
                self.setParam('CAM-applyPOS', 0)
                self.updatePVs()
                val = 0
            elif val == False:
                status = True
            else:
                false_val = True
                
            
                
        elif reason == 'useDark':
            if val == True or val == False:
                status = True
            else:
                false_val = True
                
        elif reason == 'useCalA':
            if val == True or val == False:
                status = True
            else:
                false_val = True
                
        elif reason == 'useSat':
            if val == True or val == False:
                status = True
            else:
                false_val = True
        
        elif reason == 'useEdgeDarkCor':
            if val == True or val == False:
                status = True
            else:
                false_val = True
        
        elif reason == 'useEdgeCor':
            if val == True or val == False:
                status = True
            else:
                false_val = True
                
        elif reason == 'Meas-delay':
            if 0 <= val <= 360: #not longer than 5min
                status = True 
            else:
                false_val = True
       
        elif reason == 'save':
            if val == True:
                status = True
                self.time_sav = time.strftime("%Y-%m-%d_%H-%M-%S_%Z", time.localtime())
                logging.info("\n########## \n\nsaving Data to csv with following Parameters: \n Exposure Time: %s \n Gain: %s \n Pixel Format: %s \n Sensor Bit Depth: %s \nImage Processing Parmaters: \n use BitMask: %s \n use Dark: %s \n use Calibration Faktor: %s \n##########\n\n", self.getParam('CAM-EXPT'), self.getParam('CAM-GAIN'), self.getParam('CAM-Pformat'), self.getParam('CAM-SenBitD'), self.getParam('useBitMask'), self.getParam('useDark'), self.getParam('useCalA'))
            elif val == False:
                status == True
                logging.info("\n########## \n\nsaving Data to csv stopped  \n##########\n\n")
            else:
                false_val = True
       
        elif reason[0:4] == 'LOSS' and reason != 'LOSS': #if an LOSSxx PV exept LOSS itself changed, thats when a limit LOSSxx PV changes
            if val != '':
                status = True #same as self.setParam(reason, val)
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
            #print('write PV', reason, 'to', val)
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
                   0,0,0,0,0,
                   0,0,0]
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
                            
        elif reason == 'CAM-IMAGE' and self.getParam('CAM-isMeasuring') == False: 
            numberOfImagesToGrab = 1
            try:
                self.camera.StartGrabbingMax(numberOfImagesToGrab)
            except:
                return None
            self.setParam('CAM-isMeasuring', True)
            self.updatePVs()
            grabResult = self.camera.RetrieveResult(5000, pylon.TimeoutHandling_ThrowException)
            img = grabResult.Array
                            
            img = self.SliceIMG(img)#Slice it
            if self.getParam('useDark') == True:
                img = img - self.DarkI             
            if self.getParam('useBitMask') == True:
                img = img * self.BitMask #use bitmask
  
            img_paint = f.paint_raster(img, (4,7), show = False)
            img_flip = np.fliplr(img_paint)
            
            grabResult.Release()
            self.camera.StopGrabbing()
            
            self.setParam('CAM-isMeasuring', False)
            self.updatePVs()
            return img_flip.flatten()
        
        else:
            val = self.getParam(reason) #get current value
        return val
    
    
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
        
    
    def measurement(self, Nr_img = True):
        self.StartGrabbing()

        i = 0
        t0 = time.time()
        while Nr_img:
            t1 = time.time()
            grabResult = self.camera.RetrieveResult(1000, pylon.TimeoutHandling_Return)
            if grabResult.GrabSucceeded():
                # Access the image data.
                img = grabResult.Array
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
                    arr = arr/self.getParam('CalA').reshape(splits[0], splits[1]) #divide
                # 6) Normalization (that Saturation is 1 (100%))
                if self.getParam('useSat') == True:
                    arr = arr/self.getParam('SatA').reshape(splits[0], splits[1])
                
                val = arr.flatten()
                par = np.array([int(self.getParam('useBitMask')),int(self.getParam('useDark')),int(self.getParam('useCalA'))])
                sav = np.concatenate((t1, val, par), axis=None)
                
                #save to csv File
                if self.getParam('save') == True:
                    if not os.path.exists('../Data/EPICS_GUI/'+self.time_sav+'_Data.csv'):#when file doesn't exist, first time
                          with open(os.path.join(CWD,'../Data/EPICS_GUI/'+self.time_sav+'_Data.csv'), 'wb') as file:
                                LABEL = ["Timestamp"]
                                for i in range(28):
                                    LABEL.append("LOSS"+ str(i+1))
                                LABEL.extend(["Bitmask "+str(self.getParam('BitMask-Time')), "Dark "+str(self.getParam('Dark-Time')), "Calibration Faktor "+str(self.CalA_Version )])   
                                #print(LABEL, len(LABEL))
                                np.savetxt(file, [LABEL], delimiter = ',', fmt = '%s')      
                                
                    with open(os.path.join(CWD,'../Data/EPICS_GUI/'+self.time_sav+'_Data.csv'), 'ab') as file:
                        np.savetxt(file, sav_arr,delimiter = ',')

                #save to LOSS variables
                self.setParam('LOSS', sav)
                for j in range(splits[0]*splits[1]):
                    self.setParam('LOSS'+str(j+1), sav[j+1])
                self.updatePVs()
       
                #global stop_measurement
                if self.getParam('CAM-isMeasuring') == False:
                    self.setParam('LOSS', np.zeros(splits[0]*splits[1]+1))#reset the LOSS Variabels to 0
                    grabResult.Release()
                    for j in range(splits[0]*splits[1]):
                        self.setParam('LOSS'+str(j+1), 0)
                        self.updatePVs()
                    self.camera.StopGrabbing()
                    #print('stopped Grabbing')
                    break
                    
                t2 = time.time()
                tdiff = t2-t1
            
                self.setParam('Meas-time', tdiff*1000000) #time for the process of one Measurement
                self.updatePVs()
                time.sleep(self.getParam('Meas-delay')) # in sec


    def acqBitMask(self, j=100):
        self.StartGrabbing()
        
        width = self.getParam('CAM-WIDTH')
        height = self.getParam('CAM-HEIGHT')
        Isum = np.zeros(width*height).reshape(height, width)
        for i in range(j):
            grabResult = self.camera.RetrieveResult(5000,pylon.TimeoutHandling_Return)
            if grabResult.GrabSucceeded():
                img = grabResult.Array
                # sum it up
                Isum += img 
        Img = Isum/j
            
        grabResult.Release()
        self.camera.StopGrabbing()
        
        #calculate Bitmask
        threshhold = self.getParam('BitMask-TH')
        ret, mask = cv.threshold(Img, threshhold, 1, cv.THRESH_BINARY)#ret = treshhold
        mask = np.array(mask, dtype=int) #whole image
                            
        #save whole Image of Bitmask
        with open(os.path.join(CWD,'../Calibration_Data/BitMask/_last_bitmask.npy'), 'wb') as file:
            np.save(file, mask)
        
        expt_ms = str(self.getParam('CAM-EXPT')/1000) + 'ms'
        time_txt = time.strftime("%Y-%m-%d_%H-%M-%S_%Z", time.localtime())
        #save with Time and Date -> Archiv 
        with open(os.path.join(CWD,'../Calibration_Data/BitMask/' + time_txt + '_bitmask_' + expt_ms + '.npy'), 'wb') as file:
            np.save(file, mask)
                            
        #Slice it                    
        self.BitMask = self.SliceIMG(mask)
        
        #calculate new DarkA_BM
        self.DarkI_BM = self.DarkI*self.BitMask
        self.DarkA_BM = f.split_sum(self.DarkI_BM, splits)
        for j in range(splits[0]*splits[1]):
            self.setParam('DarkA_BM'+str(j+1), self.DarkA_BM.flatten()[j])
        
        #calculate Saturation
        arr = f.split_sum(self.BitMask, splits)
        val = arr.flatten()*4095 #Max Brigthness (Nr. Pixels * Mono12)
        #print('Saturation', val)
        self.setParam('SatA', val)  
        for j in range(splits[0]*splits[1]):
                    self.setParam('SatA'+str(j+1), val[j])
        self.updatePVs()
         
        # save a Dictionary with all the Data to a .json file
        BitMask_json = {'Time': time_txt, 
                     'Timestamp' : time.time(),
                     'Threshhold': self.getParam('BitMask-TH'), 
                     'Exposure Time': self.getParam('CAM-EXPT'), 
                     'Sensor Bit Depth': self.getParam('CAM-SenBitD'), 
                     'Pixelformat': self.getParam('CAM-Pformat'), 
                     'Gain': self.getParam('CAM-GAIN'),
                     'Img Size': (self.getParam('CAM-WIDTH'), self.getParam('CAM-HEIGHT')),
                     'Slice Parameters(y_start,y_end, x_start, x_end):': (self.y_start,self.y_end,self.x_start,self.x_end),
                     'Saturation Array': tuple(np.array(self.getParam('SatA'), dtype=float))}
        #print('BitMask_json:', BitMask_json)
        with open(os.path.join(CWD,'../Calibration_Data/BitMask/_last_bitmask_parameters.json'), 'w') as file:
            json.dump(BitMask_json, file)
        #save with Time and Date -> Archiv    
        with open(os.path.join(CWD,'../Calibration_Data/BitMask/' + time_txt + '_bitmask_' + expt_ms + '.json'), 'w') as file:
            json.dump(BitMask_json, file)
                  
        self.BitMask_view = f.paint_raster(self.BitMask, (4,7), show = False)
        self.BitMask_view = np.fliplr(self.BitMask_view)
    
        self.setParam('BitMask', self.BitMask_view.flatten())
        self.setParam('BitMask-Time', time_txt)
        self.setParam('CAM-acqBitMask', False) #resets the value
        self.setParam('CAM-isMeasuring', False)#resets the isMeasuring so Camera is ready for other Grabbing
        self.updatePVs()
        
        #print('acqBitMask finished')
        logging.info('acqBitMask finished')
        return None #end of Function

    
    def acqDark(self, j=100):
        self.StartGrabbing()
        
        width = self.getParam('CAM-WIDTH')
        height = self.getParam('CAM-HEIGHT')
        DarkIsum = np.zeros(width*height).reshape(height, width)
        for i in range(j):
            grabResult = self.camera.RetrieveResult(5000,pylon.TimeoutHandling_Return)
            if grabResult.GrabSucceeded():
                img = grabResult.Array
                # sum it up
                DarkIsum += img                    
        DarkI = DarkIsum/j
    
        grabResult.Release()
        self.camera.StopGrabbing()
        
        #EdgeLoss0
        try:
            self.EdgeLoss0 = np.average(DarkI, weights = self.EdgeBM)
        except:#when weigths sum up to zero
            self.EdgeLoss0 = 1
        self.setParam('EdgeLoss0', self.EdgeLoss0)
                            
        # Slice it
        self.DarkI= DarkI[self.y_start:self.y_end,self.x_start:self.x_end]
        
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
        with open(os.path.join(CWD,'../Calibration_Data/Dark/' + time_txt + '_DarkI_' + expt_ms + '.npy'), 'wb') as file:
            np.save(file, DarkI)
            #save as _last_ for reopening
        with open(os.path.join(CWD,'../Calibration_Data/Dark/_last_DarkI.npy'), 'wb') as file:
            np.save(file, DarkI)

        # save a Dictionary with all the Data to a .json file
        dark_json = {'Time': time_txt, 
                     'Timestamp' : time.time(),
                     #'BitMask': self.getParam('useBitMask') , 
                     'Exposure Time': self.getParam('CAM-EXPT'), 
                     'Sensor Bit Depth': self.getParam('CAM-SenBitD'), 
                     'Pixelformat': self.getParam('CAM-Pformat'), 
                     'Gain': self.getParam('CAM-GAIN'),
                     'Img Size': (self.getParam('CAM-WIDTH'), self.getParam('CAM-HEIGHT')),
                     'Slice Parameters(y_start,y_end, x_start, x_end):': (self.y_start,self.y_end,self.x_start,self.x_end)}
        #print('dark_json:', dark_json)
        with open(os.path.join(CWD,'../Calibration_Data/Dark/_last_Dark_parameters.json'), 'w') as file:
            json.dump(dark_json, file)
        with open(os.path.join(CWD,'../Calibration_Data/Dark/' + time_txt + '_Dark_parameters.json'), 'w') as file:
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
        self.setParam('CAM-isMeasuring', False)#resets the isMeasuring so Camera is ready for other Grabbing
        self.updatePVs()
        
        #print('acqDarkA finished')
        logging.info('acqDark finished')
        return None #end of function
        
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

                
if __name__ == '__main__': 
    server = SimpleServer()
    server.createPV(prefix, pvdb) #create PVs based on prefix and pvdb definition
    driver = iocDriver()
    while True:
        server.process(0.01) # process CA transactions
        
# cleanup
GPIO.cleanup() # all pins