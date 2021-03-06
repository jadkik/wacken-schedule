#!/usr/bin/env python3

import json
import os
import uuid
import sys
import re
import shutil
import itertools
from collections import defaultdict

import arrow
import pytz
import requests
from icalendar import Calendar, Event
from bs4 import BeautifulSoup, NavigableString


def main_2018(f):
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

def mainiter_2019(f):
    data = json.load(f)

    utc = pytz.utc
    tzinfo = 'Europe/Berlin'
    convert_to_utc = True

    for event in data['events']:
        date_start = arrow.get(int(event['dateStart']), tzinfo=utc).to(tzinfo)
        date_end = arrow.get(int(event['dateEnd']), tzinfo=utc).to(tzinfo)
        time_start = arrow.get(event['start'], 'HH:mm')
        time_end = arrow.get(event['end'], 'HH:mm')
        start = date_start.replace(hour=time_start.hour, minute=time_start.minute)
        end = date_end.replace(hour=time_end.hour, minute=time_end.minute)
        if convert_to_utc:
            start = start.to(utc)
            end = end.to(utc)
        stage = event['stage']['title']
        bandname = ' - '.join(artist['title'] for artist in event['artists']) or event['title'] or event['performance']['title']
        assert bandname, repr(event)
        yield (start, end, bandname, stage)

def main_2019(f):
    return list(mainiter_2019(f))

def calendar(data, filtered_bands):
    cal = Calendar()

    cal.add('prodid', '-//Wacken Calendar//mkcal//EN')
    cal.add('version', '1.0.0')

    now = arrow.get().datetime

    COLORS = 'yellow green red blue aqua lime olive navy white maroon fuchsia teal silver gray'.split() # noqa
    itercolors = itertools.cycle(COLORS)
    colormap = defaultdict(lambda: next(itercolors))

    if filtered_bands is None:
        filtered_data = data
    else:
        filtered_data = (
            (startdt, enddt, bandname, stagename)
            for startdt, enddt, bandname, stagename in data
            if bandname.strip() in filtered_bands
        )

    for startdt, enddt, bandname, stagename in filtered_data:
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


def download_2018(f):
    r = requests.get('https://www.wacken.com/en/bands/running-order/', stream=True) # noqa
    r.raise_for_status()
    r.raw.decode_content = True
    shutil.copyfileobj(r.raw, f)


def download_2019(f):
    r = requests.get('https://www.wacken.com/en/program/complete-running-order/?type=1541083945&tx_woamanager_pi3%5Bfestival%5D=1&tx_woamanager_pi3%5Baction%5D=show&tx_woamanager_pi3%5Bcontroller%5D=FestivalJson&cHash=39f2661563d0203edf2cb3f3c7a4f534', stream=True) # noqa
    r.raise_for_status()
    r.raw.decode_content = True
    shutil.copyfileobj(r.raw, f)

main = main_2019
download = download_2019

if __name__ == '__main__':
    html_filename, command, *extra_args = sys.argv[1:]
    if not os.path.isfile(html_filename):
        with open(html_filename, 'wb') as f:
            download(f)

    with open(html_filename, 'r') as f:
        data = main(f)

    if command == 'rebuild':
        output_filename = extra_args[0] if extra_args else 'complete_bandlist.txt'
        with open(output_filename, 'w') as f:
            for item in data:
                _, _, bandname, _ = item
                print(bandname, file=f)
    elif command == 'generate':
        output_filename = extra_args.pop(0) if extra_args else 'out.ics'
        filter_filename = extra_args.pop(0) if extra_args else None
        filtered_bands = None
        if filter_filename:
            with open('filter.txt', 'r') as f:
                filtered_bands = [line.strip() for line in f]

        cal = calendar(data, filtered_bands)

        with open(output_filename, 'wb') as f:
            write_cal(f, cal)

