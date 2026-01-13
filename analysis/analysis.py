from Feeder import network, results

voltage_warning_trigger = 0.02
"""Bus Health"""
def stress_for_bus(bus_id, bus_dict, voltage_array):
    #get bus_index
    bus_ids, bus_to_idx, idx_to_bus =network.make_bus_index(bus_dict)
    bus_index = bus_to_idx[bus_id]
    #upper limit
    v_max = bus_dict[bus_id]['Normal V_max (pu)']
    v_max_distance = v_max - voltage_array[bus_index]
    #lower limit
    v_min = bus_dict[bus_id]["Normal V_min (pu)"]
    v_min_distance = voltage_array[bus_index]-v_min
    return v_max_distance, v_min_distance

def all_buses_stress_info(bus_dict):
    bus_ids, bus_to_idx, idx_to_bus=network.make_bus_index(bus_dict)
    for bus, data in bus_dict.items():
        #Proximity, stress calculation, status
        v_upper_margin = bus_dict[bus]['Normal Vmax (pu)'] - bus_dict[bus]['V_mag (pu)']
        v_lower_margin = bus_dict[bus]['V_mag (pu)'] - bus_dict[bus]['Normal Vmin (pu)']
        headroom = min (v_upper_margin, v_lower_margin)
        if headroom < 0:
            status = "VIOLATION"
        elif headroom < voltage_warning_trigger:
            status = 'WARNING'
        else:
            status = 'OK'
        if v_upper_margin < v_lower_margin:
            limiting_side = 'HIGH'
        else:
            limiting_side = 'LOW'
        bus_dict[bus]['Status'] = status
        bus_dict[bus]['V_margin (pu)'] = headroom
        bus_dict[bus]['Limiting side'] = limiting_side
        bus_dict[bus]['V_upper_margin (pu)'] = v_upper_margin
        bus_dict[bus]['V_lower_margin (pu)'] = v_lower_margin
        
def pv_bus_info(pv_meta_dict):
    for bus, data in pv_meta_dict['final'].items():
            #Proximity, stress calculation, status
            q_upper_margin = data['Q_max'] - data['final_q']
            q_lower_margin = data['final_q'] - data['Q_min']
            headroom = min (q_upper_margin, q_lower_margin)
            #normalize headroom
            Q_headroom_norm = headroom/(data['Q_max']-data['Q_min'])
            #estabilish warning limits
            Qwarning = .1
            critical = .02
            if Q_headroom_norm <= critical:
                status = 'CRITICAL'
            elif Q_headroom_norm <= Qwarning:
                status = 'WARNING'
            else:
                status = 'OK'
            if q_upper_margin < q_lower_margin:
                limiting_side = 'HIGH'
            else:
                limiting_side = 'LOW'
            #add info to bus
            pv_meta_dict['final'][bus].update({
            'Status': status,
            'Qmargin': headroom,
            'Limiting_side': limiting_side,
            'Q_upper_margin': q_upper_margin,
            'Q_lower_margin': q_lower_margin})


