import numpy as np
import math 
s_base = 100
#function to connect buses to an index 0-6
def make_bus_index(bus_dict):
    bus_ids = sorted(bus_dict.keys())
    bus_to_idx = {bus_id: i for i, bus_id in enumerate(bus_ids)} 
    idx_to_bus = {i: bus_id for bus_id, i in bus_to_idx.items()}
    return bus_ids, bus_to_idx, idx_to_bus

#return a power injection list to do math with
def create_power_injection_list(bus_dict):
    net_p = []
    net_q = []
    for bus, bus_data in bus_dict.items():
        net_p.append((bus_data['P_gen']/s_base-bus_data['P_MW'])/s_base)
        net_q.append(bus_data['Q_gen']/s_base-bus_data['Q_load']/s_base)
    real_array = np.array(net_p)
    img_array = np.array(net_q)
    return real_array, img_array


#create an array for specified voltages
def create_v_spec_list(bus_dict):
    v_spec=[]
    for bus_ids, bus_data in bus_dict.items():
         value = bus_data['V_spec']
         v_spec.append(value)
    v_spec_array = np.array(v_spec)
    return v_spec_array

#create and array for Qmin
def create_Q_min_list(bus_dict):
    qmin=[]
    for bus_ids, bus_data in bus_dict.items():
         value = bus_data['Q_min']/s_base
         qmin.append(value)
    qmin_array = np.array(qmin)
    return qmin_array


#create an array for Qmax
def create_Q_max_list(bus_dict):
    qmax=[]
    for bus_ids, bus_data in bus_dict.items():
         value = bus_data['Q_max']/s_base
         qmax.append(value)
    qmax_array = np.array(qmax)
    return qmax_array

#funtion to build a Y-bus matrix and initialize it to zero
def build_ybus(bus_dict):
    bus_ids, bus_to_idx, idx_to_bus = make_bus_index(bus_dict)
    n = len(bus_ids) #n is to esblish the size of of the matrix
    Ybus = np.zeros((n,n), dtype=complex)
    return Ybus, bus_ids, bus_to_idx, idx_to_bus, n

#function to add line into the Ybus
def stamp_series_line(Ybus: np.ndarray, i: int, k: int, R:float, X:float, B:float) -> complex:
    """
    Docstring for stamp_series_line
    
    Stamps one series line (R +jx) between matrix indices i and k.
    Returns the admittance y = 1/(R+jX)

    :param Ybus: Description
    :type Ybus: np.ndarray
    :param i: from
    :type i: int
    :param k: to
    :type k: int
    :param R: Resistance
    :type R: float
    :param X: Reactance
    :type X: float
    :return: Description
    :rtype: complex
    """ 
    z = R + 1j*X #impedance
    y = 1/z # admittance
    b = B/2*1j #line charging
    Ybus[i,i] += y+b #Self-admittance at Bus i
    Ybus[k,k] += y+b #Self-admittance at Bus k
    Ybus[i,k] -= y #Coupling between i and k
    Ybus[k,i] -= y #Coupling between k and i

#stamp bus shunts
def bus_shunt_stamping(Ybus: np.ndarray, i: int, gs:float, bs:float):
    B = gs+1j*bs
    Ybus[i,i] += B#Self-admittance at Bus i
  
#function to create voltages
def create_voltage(magnitude:float, degree_angle:float):
    radians = math.radians(degree_angle)
    real_part = magnitude*math.cos(radians)
    imaginary_part = magnitude*math.sin(radians)
    voltage= real_part + 1j*imaginary_part
    return voltage

def create_voltage_array(volt_list):
    volt_array = np.array(volt_list, dtype=complex)
    return volt_array

def find_slack_bus(bus_dict):
    for bus_id, bus_data in bus_dict.items():
        if bus_data['type'] == 'slack':
            slack_id = bus_id
    bus_ids, bus_to_idx, idx_to_bus = make_bus_index(bus_dict)
    slack_idx = bus_to_idx[slack_id]
    return slack_id, slack_idx

def bus_sort(bus_dict):
    #bus number list
    PQ_buses = []
    PV_buses = []
    #bus index list
    PQ_index = []
    PV_index = []
    for bus_id, bus_data in bus_dict.items():
        if bus_data['type'] == 'slack':
            slack_id = bus_id
        elif bus_data['type'] == 'PQ':
            pq_id = bus_id
            PQ_buses.append(pq_id)
        elif bus_data['type'] == 'PV':
            pv_id = bus_id
            PV_buses.append(pv_id)

    #function to get indexes
    bus_ids, bus_to_idx, idx_to_bus = make_bus_index(bus_dict)

    #define slack_idx
    slack_idx = bus_to_idx[slack_id]

    #defind PQ index
    for i in PQ_buses:
        bus_idx = bus_to_idx[i]
        PQ_index.append(bus_idx)
    
    #defind PV index
    for i in PV_buses:
        bus_idx = bus_to_idx[i]
        PV_index.append(bus_idx)
    #return 
    return slack_idx, slack_id, PQ_index, PV_index

def guass_solver(Ybus: np.ndarray, num_buses:int, i:int, p_inj:list, 
                 q_inj:list, v_list:np.array):
    sum = 0+0j
    for k in range(num_buses):
        if k != i:
            sum+= Ybus[i,k]*v_list[k]
    v_list[i] = 1/Ybus[i,i]*((p_inj[i]-q_inj[i]*1j)/v_list[i].conjugate() - sum)
    return v_list[i]

def pv_guass_solver(Ybus: np.ndarray, num_buses:int, i:int, p_inj:list, 
                 v_spec:np.array, v_list:np.array):
    sum = 0+0j
    for k in range(num_buses):
        if k != i:
            sum+= Ybus[i,k]*v_list[k]

    current_sum = 0+0j
    for k in range(num_buses):
        current_sum+= Ybus[i,k]*v_list[k]
    s = v_list[i]*current_sum.conjugate()
    q = s.imag

    v_temp = 1/Ybus[i,i]*((p_inj[i]-q*1j)/v_list[i].conjugate() - sum)
    v_list[i] = v_spec[i] * v_temp/ abs(v_temp)

    return q

#calculate slack power
def slack_power_solver(Ybus: np.ndarray, num_buses:int, v_array:np.array, slack_idx:int):
    current_sum = 0+0j
    for k in range(num_buses):
            current_sum+= Ybus[slack_idx,k]*v_array[k]
    s = v_array[slack_idx]*current_sum.conjugate()
    p = s.real #injection
    q = s.imag #injection
    return p, q

#sort slack power
def sort_slack_power(Ybus: np.ndarray, num_buses:int, v_array:np.array, slack_idx:int,slack_id, bus_dict):
    p_inj,q_inj = slack_power_solver(Ybus, num_buses, v_array, slack_idx)
    bus_dict[slack_id]['Q_net'] = q_inj *s_base
    if p_inj >= 0:
        bus_dict[slack_id]['P_gen'] = p_inj*s_base
    else:
         bus_dict[slack_id]['P_MW'] = -p_inj*s_base
    if q_inj<0:
        bus_dict[slack_id]['Q_load']=-q_inj*s_base
    else:
        bus_dict[slack_id]['Q_gen'] =q_inj*s_base


