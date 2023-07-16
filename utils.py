import os
import humanize

humanize.activate("de_DE")
import pandas as pd
import wget
import datetime
import asyncio


def download_google_sheet_as_df(id, filename="temp.csv", gid=None):
    if os.path.isfile(filename):
        os.remove(filename)
    gid_str = f"gid={gid}&" if gid else ""
    wget.download(
        f"https://docs.google.com/spreadsheets/d/{id}/export?{gid_str}format=csv",
        out=filename,
    )
    return pd.read_csv(filename)


def format_appointment(event):
    now = datetime.datetime.now() + datetime.timedelta(hours=2)  # todo timezones!
    if event.deadline > now:
        remaining = humanize.naturaldelta(event.deadline - now)
        remaining_str = f"{remaining} zum Zusagen"
    else:
        remaining_str = "Zeit abgelaufen"
    return f"{event.start.strftime('%d.%m.%Y')}: [{event.name}](<{event.url}>) ({remaining_str})"


def run_async(callback=lambda *x, **y: None):
    def inner(func):
        def wrapper(*args, **kwargs):
            def __exec():
                out = func(*args, **kwargs)
                callback(out)
                return out

            return asyncio.get_event_loop().run_in_executor(None, __exec)

        return wrapper

    return inner
