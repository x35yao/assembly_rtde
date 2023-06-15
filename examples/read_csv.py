import pandas as pd

filename = '../data/2023-06-15/1686848511'
filename = './robot_data.csv'
df = pd.read_csv(filename, sep = ' ')
dt = df['timestamp'].iloc[-1] - df['timestamp'].iloc[0]
freq = len(df) / dt
print(df['actual_q_'])
print(freq)

# print(df['output_double_register_6'])
raise
print(df['2'])
raise
print(df.shape)
print(dt)
print(freq)
print(df.keys())
