import json
import pandas as pd

json_string = '{"a":[1],"b":[2],"c":[3]}'

a_json = json.loads(json_string)
dataframe = pd.DataFrame(a_json)
print(dataframe)
