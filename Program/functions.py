""" set of Functions 
Written by: Anna Stampfli
Ussage: For the Beam Loss Project
"""

#import functions as f

import numpy as np #for working with arrays
#from numba import jit # for GPU calculations
import cv2 as cv # for opening images an painting images
from pypylon import pylon
import RPi.GPIO as GPIO # for controlling the GPIOs
from PIL import Image # for saving images out of Array
import time #for saving timestamp
import os #for information about paths
import math #for square rooot
from numba import jit # for GPU calculations
from numba import njit # for GPU calculations
import matplotlib.pyplot as plt # for plotting images and graphes
import matplotlib.image as mpimg

#setup
"""
GPIO.setmode(GPIO.BOARD)
GPIO_all = [7, 11, 12, 13, 15, 16, 18, 19, 21, 22, 23, 24, 26, 29, 31, 32, 33, 35, 36, 37, 38, 40] #Tulple (..) is also possible
GPIO.setup(GPIO_all, GPIO.OUT) #GPIO.IN for inputs
"""

#https://gist.github.com/soply/f3eec2e79c165e39c9d540e916142ae1
def show_images(images, cols = 1, titles = None):
    """Display a list of images in a single figure with matplotlib.
    
    Parameters
    ---------
    images: List of np.arrays compatible with plt.imshow.
    
    cols (Default = 1): Number of columns in figure (number of rows is 
                        set to np.ceil(n_images/float(cols))).
    
    titles: List of titles corresponding to each image. Must have
            the same length as titles.
    """
    assert((titles is None)or (len(images) == len(titles)))
    n_images = len(images)
    if titles is None: titles = ['Image (%d)' % i for i in range(1,n_images + 1)]
    fig = plt.figure()
    for n, (image, title) in enumerate(zip(images, titles)):
        a = fig.add_subplot(cols, np.ceil(n_images/float(cols)), n + 1)
        if image.ndim == 2:
            plt.gray()
        plt.imshow(image)
        a.set_title(title)
    fig.set_size_inches(np.array(fig.get_size_inches()) * n_images)
    plt.show()
    

#@njit
#@jit(nopython=True) #both worked
def sumGPU(allROI):
    brightness = np.zeros(28)
    for i in range(28):
        brightness[i] = np.sum(allROI[i])
    return brightness

#@jit(nopython=True)   
def split_sum_new(arr, splits, allROI_out = False): #with integrated flipping of image, sumGPU()
    y, x = splits
    arr_shape = np.shape(arr)
    arr = arr[0:arr_shape[0]//y*y, 0:arr_shape[1]//x*x]
    allROI = np.array(np.split(np.array(np.split(arr, x, axis=1)), y, axis=1))
    #array right shape (4(rows), 7(colums), ly,lx) and flipped so it's like NR. on box
    allROI = np.concatenate(allROI)
    #print(np.shape(allROI))
    brightness =  sumGPU(allROI)#np.sum(allROI,axis = (1,2))#
    #brightness = np.fliplr(brightness)
    if allROI_out:
        return brightness, allROI #shape first vertically then horizontally
    else:
        return brightness # spape = splits
    
def split_sum(arr, splits, allROI_out = False): #with integrated flipping of image
    y, x = splits
    arr_shape = np.shape(arr)
    arr = arr[0:arr_shape[0]//y*y, 0:arr_shape[1]//x*x]
    allROI = np.fliplr(np.array(np.split(np.array(np.split(arr, x, axis=1)), y, axis=1)))
    #array right shape (4(rows), 7(colums), ly,lx) and flipped so it's like NR. on box
    brightness = np.sum(allROI,axis = (2,3))
    if allROI_out:
        return brightness, allROI #shape first vertically then horizontally
    else:
        return brightness # spape = splits
    

def paint_raster(arr, splits, show = True):
    y, x = splits
    img_size = arr.shape
    lx = img_size[1]//x #ganzzahlige Division
    ly = img_size[0]//y
    line_color = arr.max() #linien sind so hell wie max
    #print('The shape is:', img_size, ' Divided troug:', splits, ' One slice has the size:', '(', ly, ',', lx, ')', 'Pixels per slice:', ly*lx, 'line color is', line_color)

    paint = arr.copy() # ohne .copy() wuerde es img_pos_sliced auch veraendern
    paint = np.array(paint, dtype=float) # um auch bool arrays darzustellen
    
    for j in range(y):
        dy = j*ly
        cv.line(paint, (0,dy),(img_size[1], dy), int(line_color), 1)#img,startpoint, endpoint, brigthness, thicknes
    for i in range(x):
        dx = i*lx
        cv.line(paint, (dx, 0), (dx,img_size[0]), int(line_color), 1)
    if show:
        plt.imshow(paint)
        plt.colorbar()
    return paint


def info(var):
    print("Data:", var)
    print("Data type:", var.dtype)
    print("max Value:", var.max())
    print("min Value:", var.min())
    print("Object type", type(var))
    

def reshape_allROI(allROI, splits, show = True): # Example: from (28, ly, lx) to (28. ly, lx) in other order vertically <=> horizontally
    y, x = splits
    z, ly, lx = np.shape(allROI)
    allROI = allROI.reshape(x, y, ly, lx)
    allROI = np.moveaxis(allROI, (0,1), (1,0))
    allROI = allROI.reshape(z, ly, lx) # z = x*y
    #print(np.shape(allROI))
    if show:
        show_images(allROI, cols = y)
    return allROI

def float_or_na(value): #to convert N/A (not available) to nan (not a number), nan <class 'float'>
    return float(value if value != '#N/A' and value != 'BadVal' else 'nan')


        
        
        
    