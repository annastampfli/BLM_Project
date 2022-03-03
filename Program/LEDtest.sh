#!/bin/bash

read -p "Which XX Nr. of ARIDI-BLM do you want to test? " nr
prefix="ARIDI-BLM"$nr":"
echo $prefix

for ((z=0;z<=2;z++)) 
    do 
    sleep 1
    echo "Wait for " $((3-$z)) " sec"
    done
    
for ((z=1;z<=21;z++));
    do
    echo ${prefix}"LED_"$z
    caput ${prefix}"LED_"$z 1
    sleep 0.5
    done

for ((z=1;z<=21;z++));
    do
    echo ${prefix}"LED_"$z
    caput ${prefix}"LED_"$z 0
    sleep 0.5
    done
    
sleep 1
caput ${prefix}"LEDall" 1
sleep 1 
caput ${prefix}"LEDall" 0