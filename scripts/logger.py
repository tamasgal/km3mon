import datetime
from datetime import datetime as dt
from datetime import timezone as tz
import time
import os

log_file = 'MSG_'+(dt.now(tz.utc) - datetime.timedelta(days=1)).strftime("%Y-%m-%d")+'.log'
out_file = 'MSG_'+(dt.now(tz.utc) - datetime.timedelta(days=1)).strftime("%Y-%m-%d")+'.png'

def seconds_to_UTC_midnight():
    
    tomorrow = dt.now(tz.utc) + datetime.timedelta(days=1)
    midnight = dt(year=tomorrow.year, month=tomorrow.month, 
                                 day=tomorrow.day, hour=0, minute=0, second=0, tzinfo=tz.utc)    
    return (midnight - dt.now(tz.utc)).seconds

while True: 
    os.system('python3 log_analyser.py -i '+log_file+' -o '+out_file )
    time.sleep(seconds_to_UTC_midnight() + 60)
