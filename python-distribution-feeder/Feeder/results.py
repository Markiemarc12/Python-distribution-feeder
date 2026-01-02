"File to handle result formatting logic"
import math
import numpy as np
from tabulate import tabulate 
from Feeder import network
s_base = 100
voltage_warning_trigger = 0.02
'''Bus table functions'''
def formatter(value, fmt=".2f"):
    if value is None:
        value = '-'
        return value
    if isinstance(value,str):
        value = value
        return value
    if isinstance(value,(int, float, np.floating)):
        if np.isnan(value):
            value = '_'
        else: 
            value = f"{value:{fmt}}"
        return value
    return str(value)

def voltage_fomatter(v_list):
    new_v_list = []
    for v in v_list:
        vMag = math.sqrt(v.real**2+v.imag**2)
        angle = math.degrees(math.atan2(v.imag,v.real))
        new_v_list.append((vMag,angle))
    return new_v_list

def build_bus_rows(bus_dict, voltage_array, bus_to_idx):
    new_v_list = voltage_fomatter(voltage_array)
    rows = []
    for id, data in bus_dict.items():
        idx = bus_to_idx[id]
        v_mag, v_angle = new_v_list[idx]
        row = [id, 
               formatter(data['type']),  
               formatter(v_mag, ".4f"),
               formatter(v_angle), 
               formatter(data['P_MW'], ".3f"), 
               formatter(data['P_gen'], ".3f"),
               formatter(data['Q_Mvar'], ".3f"),
               formatter(data['Q_gen'], '.3f'),
               formatter(data['Q_net'], ".3f")
               ]
        rows.append(row)
    return rows

def create_bus_data_table(bus_dict, voltage_array, bus_to_idx):  

    headers = ["Bus Id", "Bus Type", "|V| pu", "Voltage Angle (deg)", "P_load","P_gen", "Q_load", "Q_gen", 'Q_net']
    data = build_bus_rows(bus_dict, voltage_array, bus_to_idx)
  
    print("\nResults Table")
    print(tabulate(data, headers=headers, tablefmt="grid"))
    print("Note: All quantities are on a 100 MVA base unless otherwise noted.")

#add up generation
def generation_sum(bus_dict):
    q_supply = []
    p_supply =[]
    for bus, data in bus_dict.items():
        if data['type']=='slack' or data['type']=='PV':
            q_supply.append((bus,data['Q_gen']))
            p_supply.append((bus,data['P_gen']))
    p_gen = sum(item[1] for item in p_supply)
    q_gen = sum(item[1] for item in q_supply)
    return q_supply, q_gen, p_supply, p_gen

#sum load
def load_sum(bus_dict):
    q_load = []
    p_load =[]
    for bus, data in bus_dict.items():
            q_load.append((bus,data['Q_Mvar']))
            p_load.append((bus,data['P_MW']))
    p_consume= sum(item[1] for item in p_load)
    q_consume = sum(item[1] for item in q_load)
    return q_load, q_consume, p_load, p_consume

"""Summary function"""
def meta_box(bus_dict, line_list: list, tolerance: float,maxiteration: int, iterations: int, converge: bool, solver = "Gauss Siedel",case = "Case"):
    slack_bus, slack, pq_list, pv_list = network.bus_sort(bus_dict)
    print("{}\n{} buses, {} lines".format(case, len(bus_dict), len(line_list)))
    print("Bus counts: 1 slack at bus {}, {} PQ(s), {} PV(s)".format(slack,len(pq_list), len(pv_list)))
    print("Solver method: {}".format(solver))
    print("Convergence tolerance: {} \nMax iterations {}".format(tolerance,maxiteration ))
    print("Iteration used {}".format(iterations))
    if converge == True:
        answer = "Yes"
    else:
        answer = "No"
    print("Converged: {}".format(answer))
    print("----Total Generation and Total Load----")
    #supply
    _,q_total, _, p_total = generation_sum(bus_dict)
    print('Total P_MW supplied: {} pu'.format(formatter(p_total/s_base)))
    print('Net Q Supplied: {} pu'.format(formatter(q_total/s_base)))
    #load
    _,q_load, _, p_load = load_sum(bus_dict)
    print('Total P_MW consumed: {} pu'.format(formatter(p_load/s_base)))
    print('Total Q_Mvar consumed: {} pu'.format(formatter(q_load/s_base)))
    print('P_MW losses: {} pu'.format(formatter((p_total-p_load)/s_base)))
    print('Net Q injections: {} pu'.format(formatter((q_total-q_load)/s_base)))




#add voltages to dictionary
def add_voltage_solution(volt_array, bus_dict):
    v_list = voltage_fomatter(volt_array)
    bus_ids, bus_to_idx, idx_to_bus=network.make_bus_index(bus_dict)
    for bus, data in bus_dict.items():
        idx = bus_to_idx[bus]
        v_mag, v_angle = v_list[idx]
        #create new bus keys
        bus_dict[bus]['V_mag (pu)'] = float(v_mag)
        bus_dict[bus]['theta_degrees'] = float(v_angle)

def create_voltage_stress_ranking(bus_dict):
    list_of_tuples = []
    #loop through bus items and store margins
    for bus, bus_data in bus_dict.items():
        list_of_tuples.append((bus, bus_data['V_margin (pu)']))
    sorted_list = sorted(list_of_tuples, key=lambda x: x[1])
    return sorted_list

def create_stress_table(bus_dict):  
    ranking = create_voltage_stress_ranking(bus_dict)
    headers = ["Bus Id","Bus Type","Voltage (pu)","Normal Vmax","Normal Vmin","Voltage Headroom (pu)", "Status", "Limiting Side"]
    rows = []

    for bus, margin in ranking:
        data = bus_dict[bus]
        rows.append([
            bus,
            data['type'],
            data['V_mag (pu)'],
            data['Normal Vmax (pu)'],
            data['Normal Vmin (pu)'],
            formatter(margin),
            data['Status'],
            data['Limiting side']
            
        ])
  
    print("\nBus Voltage Stress Ranking")
    print(tabulate(rows, headers=headers, tablefmt="grid"))

def health_summary(bus_dict, pv_dict):
    #voltage at each bus stuff
    stress_tuples = create_voltage_stress_ranking(bus_dict)
    worst_bus_id, headroom = stress_tuples[0]
    violations = []
    warnings = []
    ok = []
    for bus, bus_data in bus_dict.items():
        if bus_data['Status'] == "VIOLATION":
            violations.append((bus,bus_data['Status']))
        elif bus_data['Status'] == "WARNING":
            warnings.append((bus,bus_data['Status']))
        elif bus_data['Status'] == "OK":
            ok.append((bus,bus_data['Status']))
    #PV bus stuff
    initial_pv = pv_dict.get("initial", {})
    final_pv = pv_dict.get("final", {})
    switched_pv = pv_dict.get("switched", {})
    print("--------Health Summary--------")
    print("--Voltage at Each bus--")
    print("Worst bus: {}; Headroom: {} pu".format(worst_bus_id, formatter(headroom,".3f")))
    print("# of VIOLATIONS: {}".format(len(violations)))
    if len(violations) != 0:
        print("Buses operating outside of limits:")
        for item in violations:
            print(item)
    print("# of buses within {} limit: {}".format(voltage_warning_trigger,len(warnings)))
    print("# of okay buses: {}".format(len(ok)))
    print("--PV Bus(es)--")
    print("Inital PV bus #: {}".format(len(initial_pv)))
    print("Final PV bus #: {}".format(len(final_pv)))
    print("Number of PV switched to PQ: {}".format(len(switched_pv)))


def create_pv_stress_ranking(pv_meta_dict):
    list_of_tuples = []
    #loop through bus items and store margins
    for bus, pv_data in pv_meta_dict['final'].items():
        list_of_tuples.append((bus, pv_data['Qmargin']))
    sorted_list = sorted(list_of_tuples, key=lambda x: x[1])
    return sorted_list
  
def create_pv_stress_report(pv_meta_dict):
     ranking = create_pv_stress_ranking(pv_meta_dict)
     headers = ["Bus Id", "Vspec (pu)", "Qmin","Qmax", "Q Final","Q Margin", "Status", "Limiting Side"]
     rows = []
     for bus, margin in ranking:
        data = pv_meta_dict['final'][bus]
        rows.append([
            bus,
            data['Vspec'],
            data["Q_min"],
            data['Q_max'],
            data['final_q'],
            formatter(margin),
            data['Status'],
            data['Limiting_side'],])
     print("\nPV Bus Q Stress Ranking")
     print(tabulate(rows, headers=headers, tablefmt="grid"))

def switched_pv_report(pv_meta_dict):
    if len(pv_meta_dict['switched']) == 0:
        print("0 PV buses switched")
    else:
        headers = ["Bus Id", "Vspec (pu)", "Qmin","Qmax", 'Qcalc_at_switch', 'Q clamped to', "Limit Hit",'Iterations Switched']
        rows = []
        for bus, data, in pv_meta_dict['switched']:
            data = pv_meta_dict['switched'][bus]
            rows.append([
                bus,
                data['Vspec'],
                data["Q_min"],
                data['Q_max'],
                data['Qcalc_at_switch'],
                data['Q_clamped_to'],
                data['limit_hit'],
                data['iter_at_switch']
            ])
        print("\nPV Buses Switched to PQ")
        print(tabulate(rows, headers=headers, tablefmt="grid"))

def create_pv_tab(pv_meta_dict):
    create_pv_stress_report(pv_meta_dict)
    switched_pv_report(pv_meta_dict)