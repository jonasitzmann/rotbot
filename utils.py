import os
import pandas as pd
import wget


def download_google_sheet_as_df(id, filename='temp.csv', gid=None):
    if os.path.isfile(filename):
        os.remove(filename)
    gid_str = f'gid={gid}&'if gid else ''
    wget.download(f'https://docs.google.com/spreadsheets/d/{id}/export?{gid_str}format=csv', out=filename)
    return pd.read_csv(filename)

def format_appointment(x):
    return f"{x['date'].strftime('%d.%m.%Y')}: [{x['name']}](<{x['url']}>)"
