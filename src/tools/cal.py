from typing import Union

import pandas as pd
import requests

from ..concepts import Group

# it's unlikely this URL will change, but should be occassionally checked
CALENDAR_URL = "https://calendar.ucf.edu"
# these holidays need to match, specifically, how UCF labels them
OBS_HOLIDAYS = {
    "spring": ["Spring Break", "Martin Luther King Jr. Day"],
    "summer": [],
    "fall": ["Veterans Day", "Labor Day", "Thanksgiving"],
}

LONG_SHORT = {"fall": "fa", "summer": "su", "spring": "sp"}
# invert `long2short`
SHORT_LONG = {k: v for v, k in LONG_SHORT.items()}

# NOTE make sure to consider 0-indexing here
SEMESTER_LEN = {"spring": 14, "summer": 10, "fall": 15}
# this fixes off-by-1 errors __on the assumption__ we stop meetings the week before
#   finals begin.
SEMESTER_LEN = {k: v - 1 for k, v in SEMESTER_LEN.items()}

NEXT_SEMESTER = {"spring": "fall", "summer": "fall", "fall": "spring"}


def temp_schedule(group: Group):
    return make_schedule(group.semester)


def make_schedule(group_or_shortname: Union[str, Group], delta: int = 7):
    # import pdb; pdb.set_trace()
    if type(group_or_shortname) == str:
        semester = group_or_shortname
        date_range, holidays = parse_calendar(semester)
        # on average, we've had 10 meetings per semester in the past
        # typically, we've started group meetings in the 3rd week of the semester
        startdate = date_range.iloc[0] + pd.Timedelta(days=delta)
    else:
        assert isinstance(group_or_shortname, Group)
        group = group_or_shortname
        date_range, holidays = parse_calendar(group.semester)
        delta *= group.frequency

        startdate = group.startdate

    dates = [startdate]
    while dates[-1] < date_range.iloc[-1]:
        dates.append(dates[-1] + pd.Timedelta(days=delta))

    # Assume a once-a-week meeting basis and build the schedule accordingly.
    meeting_dates = pd.Series(dates)

    if holidays:
        holidays = pd.concat(holidays)
        # Removes Holidays, if the array is non-empty.
        meeting_dates = meeting_dates[~meeting_dates.isin(holidays)]

    schedule = [pd.Timestamp(x) for x in meeting_dates]

    return schedule


def parse_calendar(shortname: str) -> tuple:
    longname = SHORT_LONG[shortname[:2]]
    holidays = OBS_HOLIDAYS[longname]

    # This is the URL for the calendar's JSON-based API. This will vary by institution.
    calendar_url = f"{CALENDAR_URL}/json/20{shortname[-2:]}/{longname}"

    # UCF's JSON object holds all the "events" in an "events" identifier
    ucf_parsed = requests.get(calendar_url).json()["terms"][0]["events"]
    df_calendar = pd.DataFrame.from_dict(ucf_parsed)

    # The "summary" column of the new DataFrame holds the names of the events
    summary_mask = df_calendar["summary"]
    # Events are stored as arrays. It's easier to parse this way than reducing
    #   the list-containing column to something that isn't.
    starts = df_calendar.loc[summary_mask.str.contains("Classes Begin")].iloc[0]
    ends = df_calendar.loc[summary_mask.str.contains("Classes End")].iloc[0]

    # generate a DataFrame with all possible dates (to act like a calendar)
    date_range = pd.Series(
        pd.date_range(start=starts["dtstart"][:-1], end=ends["dtstart"][:-1])
    )

    # Remove the Holidays, since we assume students won't meet on those days.
    holidays = []
    for holiday in OBS_HOLIDAYS[longname]:
        day2remove = df_calendar.loc[summary_mask.str.contains(holiday)].iloc[0]
        beg = day2remove["dtstart"][:-1]
        end = day2remove["dtend"][:-1] if day2remove["dtend"] else beg
        holidays.append(pd.Series(pd.date_range(start=beg, end=end)))

    return date_range, holidays


def get_next_semester(ctx, group: str) -> Group:
    """Infers the current semester based on today's date.

    Takes advantage of the redirection https://ucf.calendar.edu/ has built-in.
    """
    url = requests.get(CALENDAR_URL).url

    year, sem = url.replace(f"{CALENDAR_URL}/", "").split("/")

    if sem == "fall":
        year = f"{int(year) + 1}"

    sem = NEXT_SEMESTER[sem]

    return Group(semester=f"{LONG_SHORT[sem]}{year[-2:]}", name=group)
