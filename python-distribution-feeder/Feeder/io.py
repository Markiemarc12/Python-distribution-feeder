import pandas as pd

def load_case(bus_path, line_path, shunt_path):
    bus_info = pd.read_csv(bus_path)
    line_info = pd.read_csv(line_path)
    shunt_info = pd.read_csv(shunt_path)

    bus_dict = {}
    for _, row in bus_info.iterrows():
        bus_id = int(row["bus_id"])
        bus_dict[bus_id] = {
            "type": row["bus_type"],
            "P_MW": row["P_load"],
            "Q_Mvar": row["Q_load"],
            "P_gen": row['P_gen'],
            'Q_gen': row['Q_gen'],
            "Q_min": row["Q_min"],
            "Q_max": row["Q_max"],
            "V_spec": row ["V_spec_pu"],
            "Normal Vmax (pu)": row["Normal V_max (pu)"],
            "Normal Vmin (pu)": row["Normal V_min (pu)"],
            "Emergency Vmax (pu)": row["Emergency V_max (pu)"],
            "Emergency Vmin (pu)": row["Emergency V_min (pu)"],
            'shunt_type': 'none',
            'status': 'off',
            'G-shunt(pu)': 0,
            'B-shunt(pu)': 0

        }
    #add shunt info
    for _, row in shunt_info.iterrows():
        bus_id = int(row["bus id"])
        if row["Status"] == 'on' or row['Status']==1:
            bus_dict[bus_id]['shunt_type']= row['Type']
            bus_dict[bus_id]['status']=row['Status']
            bus_dict[bus_id]['G-shunt(pu)']= row['G-shunt pu']
            bus_dict[bus_id]['B-shunt(pu)']= row['B-shunt pu']
            

    line_list = [] #Create a list of dictionaries
    for _, row in line_info.iterrows():
            line_list.append({
                "from": int(row["from_bus"]),
                "to": int(row["to_bus"]),
                "R_pu": float(row["R_pu"]),
                "X_pu": float(row["X_pu"]),
                'B_pu': float(row['B_pu']),
                "status": int(row["status"])
            })
    return bus_dict, line_list

#keep track of initial PV bus
def pv_meta(bus_dict):
    pv_meta ={
          "initial" : {},
          "final" : {},
          "switched": {}
     }
    for bus, bus_data in bus_dict.items():
          if bus_data['type'] == "PV":
               pv_meta["initial"][bus]= {
                    "Vspec":bus_data.get('V_spec'),
                    "Q_min": bus_data.get('Q_min'),
                    "Q_max": bus_data.get('Q_max') }
    return pv_meta