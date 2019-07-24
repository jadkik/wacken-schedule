Export the Wacken schedule to iCalendar format

## Set up:

```bash
virtualenv -p python3 env
. env/bin/activate
pip install -r requirements.txt
```

## Running:

```bash
./mkcal.py wacken.json generate out.ics
```

This will download the JSON file from the wacken website (not sure how long the URL in the code will stay valid, it's the biggest JSON file in the network tab when you open the page), save it to `wacken.json`, parse it,
and output an iCalendar file to `out.ics`. You can import that file into Google Calendar.


## Running with filter:

First, edit the filter.txt file to contain only bands you wish to have added to your calendar. Then, pass filter.txt as an additional parameter when running mkcal.py.

```bash
./mkcal.py wacken.json generate out.ics filter.txt
```

A complete list of bands can be copied from complete_bandslist.txt into filter. If you need to rebuild the bandlist, simply run the following command:

```bash
./mkcal.py wacken.json rebuild
```


## Troubleshooting:


If there are timezone issues, play around with the `convert_to_utc = True` or `tzinfo = 'Europe/Berlin'`
variables in the code and run again. These are set to work with Google Calendar,
but I'm not sure why it does.
