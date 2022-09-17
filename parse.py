from bs4 import BeautifulSoup
from enum import Enum, auto
import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime
import numpy as np
import splus
from functools import cache
from bs4 import Tag


class Participation(Enum):
    YES = auto()
    NO = auto()
    MAYBE = auto()
    Circle = auto()
    EXCLAMINTAION = auto()
    Cross = auto()

tag_map = {
    'fa-participation-yes': Participation.YES,
    'fa-participation-no': Participation.NO,
    'fa-participation-maybe': Participation.MAYBE,
    'fa-circle': Participation.Circle,
    'fa-exclamation': Participation.EXCLAMINTAION,
    'fa-cross': Participation.Cross
}


def get_participation(reload=True):
    if reload:
        splus.save_participation()
    with open('splus.html', 'r') as f:
            soup = BeautifulSoup(f, 'html.parser')
    table_div = soup.find("div", {"class": "wrap"}).find("div", {"class": "container"})\
        .find("div", {"class": "tab-content"}).find("div", {"class": "tab-pane active"}).find("div", {"class": "table-responsive"})
    names, urls = get_events(table_div)
    dates = get_dates(table_div)
    dates = [f'{d.strftime("%d.%m.%Y")}: [{n}]({u})' for d, n, u in zip(dates, names, urls)]
    individual_participations = get_participations(table_div)
    participation_df = pd.DataFrame(individual_participations, index=dates).applymap(lambda x: x.name.lower())
    return participation_df

def get_events(table_div):
    names, urls = [], []
    table = table_div.find('table', {'class': 'table statistics'})
    for row in table.find_all('th'):
        a = row.find('a')
        if a:
            link = a['href']
            url = f'https://www.spielerplus.de' + link
            event_type = link.split('/')[1]
            id = link.split('=')[1]
            name = get_event_name(url)
            names.append(name)
            urls.append(url)
    return names, urls

@cache
def get_event_name(url):
    soup = splus.get_event_page(url)
    name = soup.find('div', {'class': 'headline_small'}).text
    return name


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
    x = get_participation(reload=False)
    print(x)