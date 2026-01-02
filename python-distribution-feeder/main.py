from Feeder.io import load_case, pv_meta
from Feeder.network import *
from Feeder.results import*
from plots import plot
from analysis import analysis
'''
Sign convention:
Power injected into network is positive
power drawn from the network is negative
'''
s_base = 100
#load in bus and line data from excel
bus_dict, line_list = load_case(r"data\Feeder_data(Buses).csv",r"data\Feeder_data(Lines).csv",r"data\Feeder_data(Shunts).csv")

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
slack_idx, slack_id, pq_idxes, pv_idxes = bus_sort(bus_dict)

v_slack = create_voltage(1,0)
voltage_array[slack_idx]= v_slack

v_spec = create_v_spec_list(bus_dict)

Q_max = create_Q_max_list(bus_dict) #for PV bus limits

Q_min = create_Q_min_list(bus_dict) #for pv bus limits

tol = 1e-6 #define the level of accuracy you want
max_iters = 50 #define the max # of iterations
iter_count = 0
error = 1.0 # initial error
converge = False #boolean to track convergence status

while error > tol and iter_count < max_iters: 
    v_old = voltage_array.copy()
    for bus in range(num_buses):
        if bus == slack_idx:
            pass
        elif bus in pq_idxes:
            guass_solver(ybus, num_buses,bus,p_injs,q_injs, voltage_array)
        elif bus in pv_idxes:
            Q_new = pv_guass_solver(ybus, num_buses, bus, p_injs, v_spec, voltage_array)
            q_injs[bus]=Q_new #update bus with new value
            bus_id = idx_to_bus[bus]
            if Q_new > Q_max[bus]:
                #clamp Q and switch PV to PQ
                Q_new = Q_max[bus]
                bus_dict[bus_id]['type']= 'PQ'
                pv_idxes.remove(bus)
                pq_idxes.append(bus)
                q_injs[bus]= Q_new
                #update pv tracking info
                pv_meta_dict["switched"][bus_id]= { **pv_meta_dict['initial'].get(bus_id, {}),
                    'Qcalc_at_switch': Q_new,
                    'Q_clamped_to': Q_max,
                    'limit_hit': "HIGH",
                    'iter_at_switch': iter_count
                    }
            elif Q_min[bus]>Q_new:
                #clamp Q and switch PV to PQ
                Q_new = Q_min[bus]
                bus_dict[bus_id]['type']= 'PQ'
                pv_idxes.remove(bus)
                pq_idxes.append(bus)
                q_injs[bus]= Q_new
                #updat pv tracking info
                pv_meta_dict["switched"][bus_id]= {
                    **pv_meta_dict['initial'].get(bus_id, {}),
                    'Qcalc_at_switch': Q_new,
                    'Q_clamped_to': Q_min,
                    'limit_hit': "LOW",
                    'iter_at_switch': iter_count
                    }
    error = max(abs(voltage_array[i] - v_old[i]) for i in range(num_buses))
    iter_count += 1

if error < tol:
    converge = True

# ------ COMMIT FINAL RESULTS TO DICTIONARIES --------

#update slack bus power
sort_slack_power(ybus, num_buses, voltage_array, slack_idx,slack_id, bus_dict)#store slack power in not put
#remeber the slack bus is the support bus it can absorb or provide reactive power 
p,q=slack_power_solver(ybus, num_buses, voltage_array, slack_idx)
print(p,q)
I = ybus[slack_idx,:] @ voltage_array
s = voltage_array[slack_idx] *np.conj(I)
print("vslack =", voltage_array[slack_idx])
print('islack =', I)
print("sslack =", s, "P,Q= ", s.real,s.imag)
p_spec = np.sum(p_injs)
q_spec = np.sum(q_injs)
print("sum specificped injections :", p_spec, q_spec)

#commiting final imaginary power in PV bus at new dict key
for bus in pv_idxes:
    bus_id = idx_to_bus[bus]
    bus_dict[bus_id]['Q_net'] = q_injs[bus]
    bus_dict[bus_id]['Q_gen'] =  bus_dict[bus_id]['Q_net'] + bus_dict[bus_id]['Q_Mvar'] 
#comiiting final imaginary power in PQ bus at new dict key
for bus in pq_idxes:
    bus_id = idx_to_bus[bus]
    bus_dict[bus_id]['Q_net'] = q_injs[bus]*s_base

#committing final pv buses to pv dict
for bus, data in bus_dict.items():
    if data['type'] == 'PV':
        pv_meta_dict['final'][bus] = { **pv_meta_dict['initial'].get(bus, {}),
                                      'final_q': data['Q_net']
                                      } 

#update bus with voltage magnitudes and angles
add_voltage_solution(voltage_array, bus_dict)
print(pv_meta_dict)
#add stress info for ranking and display
analysis.all_buses_stress_info(bus_dict) 
analysis.pv_bus_info(pv_meta_dict)

print(bus_dict)
#Print out summary
meta_box(bus_dict, line_list, tol, max_iters, iter_count, converge)
health_summary(bus_dict, pv_meta_dict)



create_bus_data_table(bus_dict, voltage_array, bus_idx)


plot.plot_voltage(bus_ids, voltage_array, 'vo')

print(pv_meta_dict)

create_stress_table(bus_dict)

create_pv_tab(pv_meta_dict)

