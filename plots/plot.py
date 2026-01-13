import numpy as np
import math
import matplotlib.pyplot as plt



def voltage_fomatter(v_list):
    new_v_list = []
    for v in v_list:
        vMag = math.sqrt(v.real**2+v.imag**2)
        angle = math.degrees(math.atan2(v.imag,v.real))
        new_v_list.append((vMag,angle))
    return new_v_list

#Create for loop to loop through all the nodes and their values over time, not used but nice to have if future changes are needed
def plot_voltage(x_buses,y_volt_list,label):
    new_y_list = voltage_fomatter(y_volt_list)
    v_magnitude_list = []
    for vr, vi in new_y_list:
        v_magnitude_list.append(vr)
    plt.figure(figsize=(9, 6)) #Set graph size
    plt.plot(x_buses, v_magnitude_list,'o-', label=label)
    plt.xlabel("Bus #") #Create label for x axis
    plt.ylabel("|V|") #Create label for y axis
    plt.title("Voltage vs Bus") #Create label for plot
    plt.legend() #Create legended for plot
    plt.show() #display plot

