from bs4 import BeautifulSoup
from enum import Enum, auto
import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime
import numpy as np
import splus


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


def get_participation():
    splus.save_participation()
    with open('splus.html', 'r') as f:
            soup = BeautifulSoup(f, 'html.parser')
    table_div = soup.find("div", {"class": "wrap"}).find("div", {"class": "container"})\
        .find("div", {"class": "tab-content"}).find("div", {"class": "tab-pane active"}).find("div", {"class": "table-responsive"})
    dates = get_dates(table_div)
    individual_participations = get_participations(table_div)
    participation_df = pd.DataFrame(individual_participations, index=dates).applymap(lambda x: x.name.lower())
    return str(participation_df)
    # print(participation_df)
    # participations_np = np.array([[p==Participation.YES for p in plist] for plist in individual_participations.values()])
    # num_participants = participations_np.sum(axis=0).astype(np.float32)
    # num_participants += 0.5 * np.array([[p==Participation.MAYBE for p in plist] for plist in individual_participations.values()]).sum(axis=0)
    # plot_participation(dates, num_participants)


def plot_participation(dates, num_participants):
    import matplotlib.dates as mdates
    plt.style.use('seaborn-whitegrid')
    dates, num_participants = [np.array(arr) for arr in [dates, num_participants]]
    plt.gca().xaxis.set_major_formatter(mdates.DateFormatter('%d.%m.%Y'))
    plt.gca().xaxis.set_major_locator(mdates.MonthLocator(interval=6))
    weekdays = np.array([d.weekday() for d in dates])
    day_masks = [weekdays == i for i in range(7)]
    for day_idx, label in [(0, 'Mo'), (1, 'Di'), (2, 'Mi'), (3, 'Do'), (4, 'Fr'), (5, 'Sa'), (6, 'So')]:
        if day_masks[day_idx].any():
            plt.scatter(dates[day_masks[day_idx]], num_participants[day_masks[day_idx]], label=label, s=15, marker='x')

    plt.legend()
    fig = plt.gcf()
    fig.set_size_inches(8, 4)
    fig.set_dpi(200)
    fig.autofmt_xdate()
    fig.suptitle('Rotpot Trainingsbeteiligung')
    plt.tight_layout()
    plt.show()


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
        # participations[name] = [tag_map[icon['data-icon']] for icon in row.find_all('svg')]
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
    x = get_participation()
    print(x)