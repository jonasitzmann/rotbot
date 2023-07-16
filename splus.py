from requests import Session
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import os
import matplotlib.pyplot as plt
import numpy as np

s = None


def login():
    global s
    email = "rotatoespotatoes@googlemail.com"
    pwd = os.environ["SPLUSPWD"]
    start_url = "https://www.spielerplus.de"
    login_url = "https://www.spielerplus.de/site/login"
    s = Session()
    s.get(start_url)
    r = s.get(login_url)
    soup = BeautifulSoup(r.content, features="lxml")
    payload = {"LoginForm[email]": email, "LoginForm[password]": pwd}
    payload["_csrf"] = soup.find("meta", dict(name="csrf-token"))["content"]
    r = s.post(login_url, data=payload)


def get_participation_website(weeks=20, days=0, weeks_before=0, start_date=None):
    if s is None:
        login()
    now = datetime.now() + timedelta(hours=2)  # todo timezones!
    if start_date:
        start_date = datetime(*start_date)
    else:
        start_date = (now - timedelta(weeks=weeks_before)).strftime("%Y-%m-%d")
    end_date = (now + timedelta(weeks=weeks, days=days)).strftime("%Y-%m-%d")
    participation_url = "https://www.spielerplus.de/participation"
    r = s.post(
        participation_url,
        data={
            "StatisticFilterForm[startdate]": start_date,
            "StatisticFilterForm[enddate]": end_date,
        },
    )
    soup = BeautifulSoup(r.content, features="lxml")
    return soup


def get_html(url):
    if s is None:
        login()
    r = s.get(url)
    soup = BeautifulSoup(r.content, features="lxml")
    return soup


def plot_api_call_time():
    login()
    days = np.linspace(1, 500, 30)
    call_times = []
    for d in days:
        t0 = datetime.now()
        get_participation_website(weeks=0, days=d)
        call_times.append((datetime.now() - t0).total_seconds())
    plt.plot(days, call_times)
    plt.gca().set_xlabel("days")
    plt.gca().set_ylabel("call duration")
    plt.suptitle("duration of splus statistics call")
    plt.show()


if __name__ == "__main__":
    plot_api_call_time()
    get_participation_website(weeks=0, days=5)
