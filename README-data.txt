README for source data

# Card data from NetrunnerDB

https://netrunnerdb.com/api/2.0/public/cards

# Event data

N.B. Cobra, Aesops, and ABR event IDs are different. Find them in the URL for
an event on each site.  Some events are not public but can be found searching
by ID. See ./aesops-index.txt and ./cobra-index.txt files and
the ./find-events-*.pl files to update them.

## Downloading from Cobra

https://tournaments.nullsignal.games/tournaments/<CobraEventID>.json

Use ./pull-cobra-event-data.pl <cobra ID> <abr id> <event name w/o date>

## Downloading from Aesops

https://www.aesopstables.net/<AesopsEventID>/abr_export

Use ./pull-aesops-event-data.pl <aesops ID> <abr id> <event name w/o date> <date of event>
Aesops doesn't include event date in the data.

## Downloading from ABR

https://alwaysberunning.net/api/entries?id=<ABREventID>

## Validating data files

Run `./validate-data-file.py <filename-{aesops,cobra}.json>`

Here's a one-liner to validate all files created in the last day:

```
find data -regextype egrep -regex ".*(aesops|cobra)\.json" -ctime 0 | xargs -n 1 ./validate-data-file.py
```

## Assembling data for tournaments array

```
perl ./assemble-tournament-array.pl $(find data -regextype egrep -regex ".*(aesops|cobra)\.json" -ctime 0) | sort
```
