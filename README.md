Export the Wacken schedule to iCalendar format

## Set up:

```bash
virtualenv env
. env/bin/activate
pip install -r requirements.txt
```

## Running:

```bash
python mkcal.py running-order.html out.ics
```

This will download the HTML file from the wacken website, save it to `running-order.html`, parse it,  
and output an iCalendar file to `out.ics`. You can import that file into Google Calendar.

## Troubleshooting:


If there are timezone issues, play around with the `convert_to_utc = True` or `tzinfo = 'Europe/Berlin'`
variables in the code and run again. These are set to work with Google Calendar,
but I'm not sure why it does.
