from Feeder.io import load_case, pv_meta
from Feeder.network import *
from Feeder.results import*
from plots import plot
from analysis import analysis
import copy
'''
Sign convention:
Power injected into network is positive
power drawn from the network is negative
'''
s_base = 100
#load in bus and line data from excel
bus_dict, line_list = load_case(r"data\New_Feeder_Data(Buses).csv",r"data\New_Feeder_Data(Lines).csv",r"data\New_Feeder_Data(Shunts).csv")

pv_meta_dict = pv_meta(bus_dict) #store initial PVs (switching helper)

#returns bus_ids,  bus_to_idx, idx_to_bus
make_bus_index(bus_dict)

# returns Ybus, bus_ids, bus_to_idx, idx_to_bus
ybus, bus_ids, bus_idx, idx_to_bus, num_buses = build_ybus(bus_dict)

#created a variable to store the length of line_list
list_size = len(line_list)

#initialized a count variable
count = 0

#initialized a while loop to stamp every line in the line_list to the ybus
while count < list_size:
    i_count = bus_idx[line_list[count]["from"]] #from bus
    k_count = bus_idx[line_list[count]["to"]] #to bus
    R_count = line_list[count]["R_pu"] #resistance
    X_count = line_list[count]["X_pu"] #reactance
    b_count = line_list[count]["B_pu"] #line charging

    stamp_series_line(ybus, i_count, k_count, R_count, X_count, b_count)
    count = count +1
#initialized a for loop to stamp every shunt to the ybus
for bus, data in bus_dict.items():
    i_count= bus_idx[bus]
    gs = data['G-shunt(pu)']
    bs = data['B-shunt(pu)']
    bus_shunt_stamping(ybus, i_count, gs, bs)




#turn power lists into negative for math
p_injs, q_injs = create_power_injection_list(bus_dict)

#Voltage array
volt_list = []
for bus in range(num_buses):
    volt_list.append(create_voltage(1,0))
voltage_array = create_voltage_array(volt_list)

#Identifying buses and creating constant slack voltage
slack_idx, slack_id, pq_idxes, pv_idxes = bus_sort(bus_dict) #return slack index, slack id, pq indexes and pv indexes

v_slack = create_voltage(1.06,0)
voltage_array[slack_idx]= v_slack

v_spec = create_v_spec_list(bus_dict)

Q_max = create_Q_max_list(bus_dict) #list for PV bus max limits

Q_min = create_Q_min_list(bus_dict) #list for pv bus min limits

tol = 1e-6 #define the level of accuracy you want
max_iters = 200 #define the max # of iterations
iter_count = 0
error = 1.0 # initial error
converge = False #boolean to track convergence status
solved_bus_dict = copy.deepcopy(bus_dict) #create a new solved bus dictionary
EPS = 1e-6 #deadband
print(bus_dict)


#solver loop
while error > tol and iter_count < max_iters: 
    #------loop handling variables------
    to_switch = False #track if a bus hits difference
    to_pq =[] #store infomation of bus that hits limits RESET each pass
    v_old = voltage_array.copy()
    #-----Main solver loop--------
    for bus in range(num_buses):
        if bus == slack_idx:
            pass
        elif bus in pq_idxes:
            guass_solver(ybus, num_buses,bus,p_injs,q_injs, voltage_array)
        elif bus in pv_idxes:
            Q_new = pv_guass_solver(ybus, num_buses, bus, p_injs, v_spec, voltage_array)
            q_injs[bus]=Q_new
            bus_id = idx_to_bus[bus]
            Qg_compare = Q_new + bus_dict[bus]['Q_load']/s_base
            if Qg_compare > Q_max[bus]+EPS and iter_count>5:
                #clamp Q 
                clamp_qnet = Q_max[bus] - bus_dict[bus_id]['Q_load']/s_base
                to_pq.append((bus,clamp_qnet, "HIGH",Qg_compare, iter_count))
                to_switch = True
            elif Q_min[bus]>Qg_compare-EPS and iter_count>5:
                clamp_qnet = Q_min[bus] - bus_dict[bus_id]['Q_load']/s_base
                to_pq.append((bus,clamp_qnet, "LOW",Qg_compare, iter_count))
                to_switch = True

    #-----handle switch logic------
    if to_switch:
        for bus, clamp_qnet, side, Qg, iter in to_pq:
            bus_id = idx_to_bus[bus]

            # switch type in dict
            solved_bus_dict[bus_id]['type'] = 'PQ'

            # update lists (now it's safe)
            if bus in pv_idxes:
                pv_idxes.remove(bus)
            if bus not in pq_idxes:
                pq_idxes.append(bus)

            # clamp the actual Qnet injection used by the solver
            q_injs[bus] = clamp_qnet

            # tracking
            pv_meta_dict["switched"][bus_id] = {
                **pv_meta_dict['initial'].get(bus_id, {}),
                'Qcalc_at_switch': Qg * s_base, # Mvar gen Q at switch
                'Q_clamped_to': (Q_max[bus] if side=="HIGH" else Q_min[bus]) * s_base,
                'limit_hit': side,
                'iter_at_switch': iter
            }
        iter_count += 1
        continue
    #------ only if no switching happened run this-------          
    error = max(abs(voltage_array[i] - v_old[i]) for i in range(num_buses))
    iter_count += 1 
    if error < tol:
        converge = True

# ------ COMMIT FINAL RESULTS TO DICTIONARIES --------

#update slack bus power
sort_slack_power(ybus, num_buses, voltage_array, slack_idx,slack_id, solved_bus_dict)#store slack power input
#remeber the slack bus is the support bus it can absorb or provide reactive power 


#commiting final imaginary power in PV bus at new dict key
for bus in pv_idxes:
    bus_id = idx_to_bus[bus]
    solved_bus_dict[bus_id]['Q_net'] = q_injs[bus]*s_base
    solved_bus_dict[bus_id]['Q_gen'] =  solved_bus_dict[bus_id]['Q_net'] + solved_bus_dict[bus_id]['Q_load'] 
#comiiting final imaginary power in PQ bus at new dict key
for bus in pq_idxes:
    bus_id = idx_to_bus[bus]
    solved_bus_dict[bus_id]['Q_net'] = q_injs[bus]*s_base
    solved_bus_dict[bus_id]['Q_gen']  = solved_bus_dict[bus_id]['Q_net'] + solved_bus_dict[bus_id]['Q_load'] 

#committing final pv buses to pv dict
for bus, data in solved_bus_dict.items():
    bus_index = bus_idx[bus]
    if data['type'] == 'PV':
        pv_meta_dict['final'][bus] = { **pv_meta_dict['initial'].get(bus, {}),
                                      'final_q': data['Q_net'] + data['Q_load']
                                      } 

#update bus with voltage magnitudes and angles
add_voltage_solution(voltage_array, solved_bus_dict)

#add stress info for ranking and display
analysis.all_buses_stress_info(solved_bus_dict) 
analysis.pv_bus_info(pv_meta_dict)

#Print out summary
meta_box(solved_bus_dict, line_list, tol, max_iters, iter_count, converge)
health_summary(solved_bus_dict, pv_meta_dict)


create_bus_data_table(solved_bus_dict, voltage_array, bus_idx)


plot.plot_voltage(bus_ids, voltage_array, 'vo')

print(pv_meta_dict)

create_stress_table(solved_bus_dict)

create_pv_tab(pv_meta_dict)

print(solved_bus_dict[8])