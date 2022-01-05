""" set of Parameters which should not change
Written by: Anna Stampfli
Ussage:     Beam Loss Monitor Project
"""

import numpy as np

#from parameters import *

bit12 = 4095
bit8 = 255


#Positioning
#slicing parameters
y_start = 50
y_end = 280
x_start = 30
x_end = 430
Lx = x_end - x_start # whole Length  (lx = Length of one slice)
Ly = y_end - y_start


#Default Camera settings

pformat = "Mono12" 
SenBitD = "Bpp12"
expt = 32000
acqFR = 100
eacqFR = True
exau = "Off"
gain = 0
binhM = "Sum"
binh = 4
binvM = "Sum"
binv = 4

#LED on GPIO
LED_all = [40, 38, 37, 36, 35, 33, 32, #right order
           22, 21, 19, 18, 16, 15, 13, #right order
           23, 24, 26, 29, 31, 
               7, 11, 12] 

LED_all_old = [7, 11, 12, 13, 15, 16, 18, 19, 21, 22, 23, 24, 26, 29, 31, 32, 33, 35, 36, 37, 38, 40] #Tulple (..) is also possible
LED_row1 = [40, 38, 37, 36, 35, 33, 32]#right order
LED_row2 = [22, 21, 19, 18, 16, 15, 13]#right order
LED_row3 = [23, 24, 26, 29, 31]#check connection ???
LED_row4 = [7, 11, 12]

LED1 = 40
LED2 = 38
LED3 = 37
LED4 = 36
LED5 = 35
LED6 = 33
LED7 = 32

LED8 = 22
LED9 = 21
LED10 = 19
LED11 = 18
LED12 = 16
LED13 = 15
LED14 = 13



#Analyse
splits = (4, 7)


#for the graph
labels = ('1 Injector',  
          '2 S1F01', 
          '3 S1F02', 
          '4 S1F03', 
          '5 S2F01', 
          '6 S2F02', 
          '7 S2F03', 
          '8 S3F01',
          '9 S3F02', 
          '10 S3F03',
          'ARIDI-PCT2:CURRENT [mA?]', 
          'ARIDI-PCT:TAU-HOUR [h]', 
          'ABRDI-ICT-1:Q-CHRG [nC]', 
          'ALIDI-ICT-1:AVG-CHRG [nC]', 
          'ARIDI-PCT:CURRENT [mA]')
colors = ((255, 192, 0), #orange
          (146, 208, 80), #light green
          (0, 176, 80), #green
          (0, 176, 240), #light blue
          (0, 112, 192), #blue
          (0, 32, 96), #dark blue
          (112, 48, 160), #purple
          (192, 0, 0), #dark red
          (255, 0, 0), #red
          (247, 150, 70), #orange, accent 6
          (255, 85, 255), #pink for fiber 11 undulator
          (0, 0, 0), #black
          (64,64, 64), #dark grey
          (127, 127, 127), #grey
          (191, 191, 191), #light grey
          (196, 188, 150), #tan, Background 2, 25%Darker
         )

colors_RGBA = np.array(colors)/255