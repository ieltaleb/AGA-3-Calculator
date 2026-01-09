import pandas as pd
import numpy as np
import sys
sys.path.append('/content/AGA3')
import aga3

# Load your CSV (replace 'your_file.csv' with actual path if CSV, here using Excel if needed)
df = pd.read_csv("/content/Meter_calcs_AGA-3V3.csv")  # or pd.read_excel(...) if Excel

# Replace -99999 with NaN
df.replace(-99999, np.nan, inplace=True)

# Map columns to variables
df['T_f'] = df['Modeled Gas Temp (degF)']
df['P_f'] = df['Static Pressure']
df['dP'] = df['Gas Diff']  # in H2O
df['d_orifice'] = df['Plate']
df['rho_f'] = df['Density-DryGas']

# Set default constants
D_pipe = 3.826
alpha_orifice = 9.25e-6
alpha_pipe = 6.2e-6
T_r = aga3.T_r
k = 1.3198
mu = 0.012
rho_b = 0.05003
downstream_tap = False

# Function for a single row calculation
def aga3_row(row):
    if pd.isna(row['dP']) or pd.isna(row['P_f']) or pd.isna(row['T_f']) or pd.isna(row['d_orifice']) or row['dP'] <= 0 or row['rho_f'] <= 0:
        return pd.Series([np.nan, np.nan])  # skip rows with missing or invalid data

    # a. Orifice geometry
    d = aga3.thermal_expansion(alpha_orifice, row['d_orifice'], T_r, row['T_f'])
    D = aga3.thermal_expansion(alpha_pipe, D_pipe, T_r, row['T_f'])
    beta = aga3.diameter_ratio(d, D)
    E_v = aga3.velocity_factor(beta)
    C_d0, C_d1, C_d2, C_d3, C_d4 = aga3.discharge_constants(D, beta)

    # b. Flowing pressure
    P_f = row['P_f']
    if downstream_tap:
        P_f = aga3.upstream_pressure(P_f, row['dP'])

    rho_f = row['rho_f']

    # d. Expansion factor
    Y = aga3.expansion_factor(beta, row['dP'], P_f, k) if k > 0 else 1.0

    # e. Iteration factor
    F_I = aga3.iteration_flow_factor(d, D, row['dP'], E_v, mu, rho_f, Y)

    # f. Discharge coefficient
    C_dFT, _ = aga3.discharge_coefficient(C_d0, C_d1, C_d2, C_d3, C_d4, F_I)

    # g. Flows
    q_v = aga3.actual_flow(C_dFT, d, row['dP'], E_v, rho_f, Y)
    q_b = aga3.base_flow(C_dFT, d, row['dP'], E_v, rho_b, rho_f, Y)

    # Convert to MCF/D
    q_v_MCFD = q_v * 24.0 / 1000.0
    q_b_MCFD = q_b * 24.0 / 1000.0

    return pd.Series([q_v_MCFD, q_b_MCFD])

# Apply calculation row-wise
df[['q_v_MCFD', 'q_b_MCFD']] = df.apply(aga3_row, axis=1)

# Save results
df.to_csv("/content/aga3_results.csv", index=False)

print(df.head())
