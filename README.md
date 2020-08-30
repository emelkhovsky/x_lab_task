### x_lab_task

# main.py
This script needs in order to recognize audio. It uses ***Python*** and also lib ***tinkoff_voicekit_client*** for recognition. 

It takes:

* ***file.wav***
* ***phone number***
* ***database flag(0 or 1 if you want to make a writing to the database)***
* ***recognition stage(1 or 2, 1 - if you want to identify person or answering machine is on audio, 2 - if you want to understand if the person is busy or no)***

You will get a text as the result of recognition and the result of recognition stage.
Then there will be a writing to the logfile and a writing to a database table(its name is VOICEKIT_DATABASE), that(logfile contains the same fields) contain such fields as:

* ***date***
* ***time***
* ***id***
* ***result(depending on a recognition stage)***
* ***phone number***
* ***length of audio***
* ***result text***

Besides, it has a separate logfile for errors.


# sql_request

In addition to the last conditions in VOICEKIT_DATABASE there is 2 other tables: SERVER and PROJECT.
SERVER contains id, name and others data. PROJECT contains the same fields.
VOICEKIT_DATABASE has 2 additional columns(foreign keys with these 2 tables).

Task: create the sql-request that will show date(or time interval), result. For every result there must be amount per every date(if it is an interval), 
total length of audios per date, project and server.
