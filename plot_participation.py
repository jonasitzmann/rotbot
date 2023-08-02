import datetime
import numpy as np
from parse import update_participation
from pickle import load, dump
from parse import EventType, Participation
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import matplotlib


def main():
    # plotting preparation
    fig, ax = plt.subplots(figsize=(9, 4), dpi=350)
    cmap = matplotlib.cm.get_cmap("Spectral")
    url2event, participation = get_participation(download=False)
    urls = participation["url"]
    names = [n for n in participation.columns if n != "url"]
    participation = participation == Participation.YES.name.lower()
    participation.astype(np.float32)
    participation["url"] = urls
    for key in "type start name location".split():
        participation[key] = participation["url"].apply(
            lambda url: getattr(url2event[url], key)
        )
    participation.sort_values(by="start")
    only_trainings = participation[participation["type"] == EventType.TRAINING]
    # only_monday_trainings = only_trainings[only_trainings['start'].apply(lambda date: date.weekday() >= 0)]
    df = only_trainings

    def is_in_time_window(date_1, date_2):
        days_between = (date_2 - date_1).days
        return 0 <= days_between <= 30

    date_to_num_people_per_prob = {}
    df = df.reset_index()

    # challenge
    challenge_dates = [datetime.datetime(*x) for x in [(2022, 3, 6), (2022, 5, 17)]]
    ax.axvspan(
        *challenge_dates,
        ymin=0,
        ymax=50,
        alpha=1,
        color="gray",
        label="challenge",
        zorder=0,
    )
    half_rate = 14

    # draw color bars
    for i, training in df.iterrows():
        start: datetime.datetime = training["start"]
        x = start
        context = df[df["start"].apply(lambda x: is_in_time_window(x, start))]
        if (
            len(context) == 1
        ):  # add np.nan as gaps in the plots where there is no context
            date_to_num_people_per_prob[start - datetime.timedelta(days=1)] = {
                1: np.nan
            }
        time_difference = np.array(
            [(start - x["start"]).days for i, x in context.iterrows()]
        )
        weights = 0.5 ** (time_difference / half_rate)
        simple_average = False
        if simple_average:
            weights = np.ones_like(weights)
        weights /= sum(weights)
        context_participation = context[names].to_numpy()
        rel_participations: np.array = (context_participation * weights[:, None]).sum(
            axis=0
        )
        sorted_unique = sorted(set(rel_participations), reverse=True)
        num_people_per_prob = {}
        previous_num_people = 0
        for prob in sorted_unique:
            num_people = len(
                [person for person in rel_participations if person >= prob]
            )
            num_people_per_prob[prob] = num_people
            color = cmap(prob)
            if prob > 0:
                ax.plot(
                    [x, x],
                    [previous_num_people, num_people],
                    color=color,
                    lw=2,
                    zorder=0,
                )
                previous_num_people = num_people
            if not 1 in num_people_per_prob:
                num_people_per_prob[1] = 0
        date_to_num_people_per_prob[start] = num_people_per_prob

    # plot mixed dm
    dm_dates = [datetime.datetime(*x) for x in [(2022, 5, 28), (2022, 9, 3)]]
    ax.vlines(dm_dates, 0, 50, color="blue")
    # scatter tournaments / games / events
    for event_type, color in [
        (EventType.TOURNAMENT, "blue"),
        (EventType.GAME, "green"),
        (EventType.EVENT, "black"),
    ]:
        df = participation[participation["type"] == event_type]
        ax.scatter(
            df["start"],
            np.zeros(len(df)) - 1,
            color=color,
            label=event_type.name.lower(),
            marker="^",
        )
    # draw lines for concrete participations
    for prob in [0.25, 0.5, 0.75, 0.95]:
        darkness = 0.3
        color = (
            np.array(cmap(prob)) * (1 - darkness) + np.array([0, 0, 0, 1]) * darkness
        )
        num_people_list = [
            (d[min([p for p in list(d.keys()) if p >= prob])])
            for d in date_to_num_people_per_prob.values()
        ]
        ax.plot(
            date_to_num_people_per_prob.keys(),
            num_people_list,
            color=color,
            label=prob,
            lw=2,
        )

    # Set major and minor date tick locators
    maj_loc = mdates.MonthLocator(bymonth=np.arange(1, 12, 4))
    ax.xaxis.set_major_locator(maj_loc)
    min_loc = mdates.MonthLocator()
    ax.set_xlabel(
        f"Datum (Betrachtet wird EMA der letzten 30 Tage mit Halbierung alle {half_rate} Tage)"
    )
    ax.set_ylabel("Teamgröße mit Mindestbeteiligung X")
    ax.xaxis.set_minor_locator(min_loc)
    fig.suptitle("Teamgröße nach Zeit und Beteiligung")
    zfmts = ["", "%b\n%Y", "%b", "%b-%d", "%H:%M", "%H:%M"]
    maj_fmt = mdates.ConciseDateFormatter(
        maj_loc, zero_formats=zfmts, show_offset=False
    )
    ax.xaxis.set_major_formatter(maj_fmt)
    plt.grid(zorder=0, color="black")
    plt.legend(ncol=2)
    plt.tight_layout()
    plt.show()


def get_participation(download=False, start_date=(2019, 1, 1)):
    if download:
        url2event, participation = update_participation(
            future_weeks=0, update_async=False, start_date=start_date
        )
        with open("past_participation.pck", "wb") as f:
            dump((url2event, participation), f)
    with open("past_participation.pck", "rb") as f:
        url2event, participation = load(f)
    return url2event, participation


if __name__ == "__main__":
    main()
