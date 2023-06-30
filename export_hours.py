from parse import EventType, Event, Participation
from datetime import datetime
from plot_participation import get_participation
import pandas as pd


def main(starting_date=None):
    starting_date = datetime(2022, 12, 1)
    download=False
    url2event, participation = get_participation(download=download, start_date=(starting_date.year, starting_date.month, starting_date.day))
    indoor_location = 'Sackring 13'
    trainings = []
    for url, e in url2event.items():
        if e.start >= starting_date and e.type == EventType.TRAINING:
            e: Event
            location: str = e.location or indoor_location
            location = location.replace('Braunschweig, Deutschland', 'BS')
            time = f"{e.start.strftime('%H:%M Uhr')} - {e.end.strftime('%H:%M Uhr')}"
            num_participants = sum((participation[participation.url == url] == Participation.YES.name.lower()).values[0])
            duration = (e.end - e.start).total_seconds() / 3600.
            trainings.append(dict(Datum=e.start.strftime('%d.%m.%y'),Ort=location,Uhrzeit=time,Dauer=duration,Teilnehmer=num_participants))
    df = pd.DataFrame(trainings)
    total_duration = df['Dauer'].sum()
    print(f'{total_duration=}')
    df.iloc[::-1].to_csv('trainings.csv', index=False)


if __name__ == '__main__':
    main()