import pandas as pd


df = pd.read_excel('./adress.xlsx', sheet_name='簡體')
json_data = df.to_json(orient='records', force_ascii=False)

with open('example.json','w',encoding='UTF-8') as file :
  file.write(json_data)

