import pandas as pd

columns=['A', 'B', 'C', 'D', 'E']
index=['X','Y', 'Z']

df_ = pd.DataFrame(index=index, columns=columns)
df_ = df_.fillna(0) 

df_.set_value('X','A', 1)
df_.set_value('X','B', 1)
df_.set_value('Z','C', 1)

s = pd.Series([100, 100, 100], index=index)

print(df_)
print(s)

result = df_.mul(s, axis=0)
print(result)

print(result.sum())

print("")