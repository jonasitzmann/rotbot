from bs4 import BeautifulSoup
import re
from enum import Enum, auto
import pandas as pd
from datetime import datetime, timedelta
import time
import splus
from functools import cache
import config
import numpy as np
from dataclasses import dataclass
from typing import Optional


class Participation(Enum):  # ordered by probability of participation
    NO = auto()
    Cross = auto()
    EXCLAMINTAION = auto()
    MAYBE = auto()
    Circle = auto()
    YES = auto()


class EventType(Enum):
    TRAINING = auto()
    TOURNAMENT = auto()
    GAME = auto()
    EVENT = auto()


str2e_type = {
    'training': EventType.TRAINING,
    'tournament': EventType.TOURNAMENT,
    'game': EventType.GAME,
    'event': EventType.EVENT
}

tag_map = {
    'fa-participation-yes': Participation.YES,
    'fa-participation-no': Participation.NO,
    'fa-participation-maybe': Participation.MAYBE,
    'fa-circle': Participation.Circle,
    'fa-exclamation': Participation.EXCLAMINTAION,
    'fa-cross': Participation.Cross
}

def get_ttl_hash():
    return round(time.time() / config.d_update_events.total_seconds())


def get_participation():
    soup = splus.get_participation_website()
    table_div = soup.find("div", {"class": "wrap"}).find("div", {"class": "container"})\
        .find("div", {"class": "tab-content"}).find("div", {"class": "tab-pane active"}).find("div", {"class": "table-responsive"})
    urls = get_event_urls(table_div)
    individual_participations = get_participations(table_div)
    participation_df = pd.DataFrame(individual_participations).applymap(lambda x: x.name.lower())
    participation_df['url'] = urls
    url2events = {url: get_event(url, get_ttl_hash()) for url in urls}
    print('updated participations')
    return url2events, participation_df.iloc[::-1]


def get_event_urls(table_div):
    urls = []
    table = table_div.find('table', {'class': 'table statistics'})
    for row in table.find_all('th'):
        a = row.find('a')
        if a:
            link = a['href']
            url = f'https://www.spielerplus.de' + link
            urls.append(url)
    return urls


@dataclass
class Event:
    name: str
    type: EventType
    start: datetime
    deadline: datetime
    url: str
    location: str

def get_form_entry(soup, id):
    return soup.find('input', dict(id=id)).get('value')

def str2datetime(x):
    return datetime.strptime(x, '%d.%m.%Y %H:%M')


@cache
def get_event(url, ttl_hash):  # ttl_has is for updating the cash after some time
    update_url = url.replace('view', 'update')
    e_type = str2e_type[url.rsplit('/', 2)[1]]
    soup = splus.get_html(update_url)
    e_type_str = e_type.name.lower()
    if e_type == EventType.GAME:
        name = 'Spiel gegen ' + get_form_entry(soup, 'game-opponentname')
    else:
        name = get_form_entry(soup, e_type_str + '-name')
    start_date = get_form_entry(soup, 'datetime-startdate-disp')
    start_time = get_form_entry(soup, 'datetime-starttime-disp')
    deadline = str2datetime(get_form_entry(soup, e_type_str + '-participationdate-disp'))
    location = get_form_entry(soup, 'teamlocation-autocomplete')
    start = str2datetime(f'{start_date} {start_time}')
    event = Event(name, e_type, start, deadline, url, location)
    print(f'updated {e_type.name} {name} on {start}')
    return event


def get_participations(table_div):
    table = table_div.find('table', {'class': 'table statistics'}).find('tbody')
    participations = {}
    for row in table.find_all('tr'):
        name = row.text.strip().split('\n')[0]
        participations[name] = []
        for date in row.find_all('td'):
            for x in date.find_all('i'):  # zero or one
                cls = x['class'][0]
                participations[name].append(tag_map[cls])
    return participations


def parse_dates(dates, start_year=2022):
    current_year, current_month = start_year, int(dates[0].split('.')[1])
    parsed_dates = []
    for date in dates:
        day, month = [int(x) for x in date.split('.')]
        if month > current_month:
            current_year -= 1
        current_month = month
        parsed_dates.append(datetime(current_year, current_month, day))
    return parsed_dates


def get_dates(table_div):
    table = table_div.find('table', {'class': 'table statistics'})
    header = table.find('thead')
    dates = header.text.strip().split('\n')[2].split(' ')
    dates = parse_dates(dates)
    return dates


def get_names(table_div):
    names_col = table_div.find('table', {'class': 'table statistics fixed-column'})
    names_list = list(filter(lambda x: x != '', names_col.text.split('\n')))[1:]
    print('\n'.join(names_list))
    return names_list


if __name__ == '__main__':
    # event = get_event('https://www.spielerplus.de/tournament/view?id=761682')
    event = get_event('https://www.spielerplus.de/training/view?id=35670975')
    print(event)
