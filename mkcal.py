#!/usr/bin/env python3

import os
import uuid
import sys
import re
import shutil
from collections import defaultdict

import arrow
import pytz
import requests
from icalendar import Calendar, Event
from bs4 import BeautifulSoup, NavigableString


def main(f):
    soup = BeautifulSoup(f, "html.parser")

    href_days = {x.attrs['href'][-6:]: x.text for x in soup.select('a[href*="https://www.wacken.com/en/bands/running-order/#roday"]')} # noqa

    data = []
    utc = pytz.utc
    tzinfo = 'Europe/Berlin'
    convert_to_utc = True

    for anchor in (soup.select('a[name={}]'.format(x))[0] for x in href_days):
        day = href_days.get(anchor.attrs['name'])
        for div in anchor.next_siblings:
            if isinstance(div, NavigableString) or 'hidden-xs' not in div.attrs['class']: # noqa
                continue
            content = div.select('div.col-sm-38')
            for stage in content:
                child_divs = stage.find_all('div', recursive=False)
                if len(child_divs) != 2:
                    continue
                title_div, item_div = child_divs
                stage = title_div.find('img').attrs['src'].split('/')[-1]
                bands = [re.match(r'(\d{2}:\d{2}) - (\d{2}:\d{2}) (.+)', x.text.strip()) for x in item_div.find_all('div', recursive=False)] # noqa
                bands = [b.groups() for b in bands if b]
                for b in bands:
                    startdt = arrow.get('{} {}'.format(day, b[0]), 'dddd MM/DD/YYYY HH:mm').replace(tzinfo=tzinfo) # noqa
                    enddt = arrow.get('{} {}'.format(day, b[1]), 'dddd MM/DD/YYYY HH:mm').replace(tzinfo=tzinfo) # noqa
                    bandname = b[2]
                    stagename = stage
                    if startdt.hour < 11:
                        startdt = startdt.replace(hours=24)
                    if enddt.hour < 11:
                        enddt = enddt.replace(hours=24)
                    if convert_to_utc:
                        data.append((startdt.to(utc), enddt.to(utc), bandname, stagename)) # noqa
                    else:
                        data.append((startdt, enddt, bandname, stagename))
            break

    stages = {stage: ' '.join(stage[:-4].split('_')).title() for startdt, enddt, bandname, stage in data} # noqa

    return [(startdt, enddt, bandname, stages[stage]) for startdt, enddt, bandname, stage in data] # noqa


def calendar(data, filtered_bands):
    cal = Calendar()

    cal.add('prodid', '-//Wacken Calendar//mkcal//EN')
    cal.add('version', '1.0.0')

    now = arrow.get().datetime

    COLORS = 'yellow green red blue aqua lime olive navy white maroon fuchsia teal silver gray'.split() # noqa
    itercolors = iter(COLORS)
    colormap = defaultdict(lambda: next(itercolors))

    if filtered_bands == []:
        for startdt, enddt, bandname, stagename in data:
            event = Event()

            event.add('uid', '{}/{}@wacken'.format(uuid.uuid1(), '0'))
            event.add('summary', '{} / {}'.format(bandname, stagename))
            event.add('description', '')
            event.add('dtstart', startdt.datetime)
            event.add('dtend', enddt.datetime)
            event.add('dtstamp', now)
            event.add('created', now)
            event.add('last-modified', now)
            event.add('location', 'Wacken, Germany')
            event.add('class', 'PUBLIC')
            event.add('color', colormap[stagename])
            event.add('categories', colormap[stagename])

            cal.add_component(event)
    else:
        for startdt, enddt, bandname, stagename in data:
            if bandname in filtered_bands:
                event = Event()

                event.add('uid', '{}/{}@wacken'.format(uuid.uuid1(), '0'))
                event.add('summary', '{} / {}'.format(bandname, stagename))
                event.add('description', '')
                event.add('dtstart', startdt.datetime)
                event.add('dtend', enddt.datetime)
                event.add('dtstamp', now)
                event.add('created', now)
                event.add('last-modified', now)
                event.add('location', 'Wacken, Germany')
                event.add('class', 'PUBLIC')
                event.add('color', colormap[stagename])
                event.add('categories', colormap[stagename])

                cal.add_component(event)

    return cal


def write_cal(f, cal):
    f.write(cal.to_ical())


def download(f):
    r = requests.get('https://www.wacken.com/en/bands/running-order/', stream=True) # noqa
    r.raise_for_status()
    r.raw.decode_content = True
    shutil.copyfileobj(r.raw, f)


if __name__ == '__main__':
    if not os.path.isfile(sys.argv[1]):
        with open(sys.argv[1], 'wb') as f:
            download(f)

    with open(sys.argv[1], 'r') as f:
        data = main(f)

    if sys.argv[2] == 'rebuild':
        with open('complete_bandlist.txt', 'w') as f:
            for bandname in data:
                f.write(bandname[2] + '\n')
        sys.exit()

    filtered_bands = []
    if len(sys.argv) == 4:
        with open('filter.txt', 'r') as f:
            for line in f:
                filtered_bands.append(line.split('\n')[0])

    cal = calendar(data, filtered_bands)

    with open(sys.argv[2], 'wb') as f:
        write_cal(f, cal)
