import pandas as pd

dict_scores = {"english": 80, "chinese": 60, "math": 70}


series_score = pd.Series(dict_scores)

print(series_score["english"] + series_score["chinese"])
