import pandas as pd

df = pd.DataFrame([[2, 3], [5, 6], [8, 9]],
    index=['cobra', 'viper', 'sidewinder'],
    columns=['max_speed', 'shield'])
print(df.loc['viper'])
