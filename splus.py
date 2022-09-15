from requests import Session
from bs4 import BeautifulSoup
from datetime import datetime, timedelta

s = None

def login():
    global s
    email = 'rotatoespotatoes@googlemail.com'
    pwd = 'hotrotbot'
    start_url = 'https://www.spielerplus.de'
    login_url = 'https://www.spielerplus.de/site/login'
    s = Session()
    s.get(start_url)
    r = s.get(login_url)
    soup = BeautifulSoup(r.content, features="lxml")
    payload = {'LoginForm[email]': email, 'LoginForm[password]': pwd}
    payload['_csrf'] = soup.find('meta', dict(name='csrf-token'))['content']
    r = s.post(login_url, data=payload)


def save_participation():
    if s is None:
        login()
    now = datetime.now()
    start_date = now.strftime('%Y-%m-%d')
    end_date = (now + timedelta(weeks=1)).strftime('%Y-%m-%d')
    participation_url = 'https://www.spielerplus.de/participation'
    r = s.post(participation_url, data={
        'StatisticFilterForm[startdate]': start_date,
        'StatisticFilterForm[enddate]': end_date})
    soup = BeautifulSoup(r.content, features='lxml')
    with open('splus.html', 'w') as f:
        f.write(str(soup))


if __name__ == '__main__':
    save_participation()
