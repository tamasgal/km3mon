import sys
import re
import numpy as np
import matplotlib.pyplot as plt
import os
import datetime
from datetime import datetime as dt
from datetime import timezone as tz
import time

class Message:   
    def __init__(self, msg):
        self.regexp  = '(\w+.\w+)\s+\[(\w+)\]:\s+(\w+\s+\w+\s+\d+\s+\d+:\d+:\d+\s+\d+)\s+(\d+\.\d+\.\d+\.\d+)\s+(\w+\/*\w+)\s+(\w+)\s+(.*)'
        self.matches = re.match(self.regexp,msg)
        self.fields  = re.split(self.regexp,msg)
    
    def is_error(self):
        return self.matches!=None and self.fields[6]=='ERROR'
    def is_warning(self):
        return self.matches!=None and self.fields[6]=='WARNING'
    def get_process(self):
        if (self.matches!=None):
            return self.fields[2]

def plot_log_statistics(errors,warnings,title,output):

    err_keys = [k for k in sorted(errors  .keys() , key=str.casefold)]
    war_keys = [k for k in sorted(warnings.keys() , key=str.casefold)]

    if (err_keys != war_keys):
        sys.exit("plot_log_statistics ERROR: Dictionaries with different keys") 
        
    x_labels = [str(k) for k in err_keys]
    x        = np.arange(len(x_labels))
    y_e      = [errors  [k] for k in err_keys ]
    y_w      = [warnings[k] for k in war_keys ]

    fig = plt.figure()
    ax  = fig.add_subplot(111)
    
    bar_width = 0.25
    err_plt   = ax.bar(            x, y_e, bar_width, color = 'r')
    war_plt   = ax.bar(x + bar_width, y_w, bar_width, color = 'b')

    ax.set_ylabel('Counts')
    ax.set_xticks(x + 0.5*bar_width)
    ax.set_xticklabels(x_labels)
    ax.legend((err_plt, war_plt), ('errors', 'warnings'))
    ax.set_ylim(1e-1,1e6)
    ax.set_yscale('log')
    ax.grid(True)

    plt.title(title)
    plt.savefig(output)
    
def seconds_to_UTC_midnight():    

    tomorrow = dt.now(tz.utc) + datetime.timedelta(days=1)
    midnight = dt(year=tomorrow.year, month=tomorrow.month, 
                                 day=tomorrow.day, hour=0, minute=0, second=0, tzinfo=tz.utc)    
    return (midnight - dt.now(tz.utc)).seconds

def main():
    
    while True: 
        log_file = './../logs/MSG_'+(dt.now(tz.utc) - datetime.timedelta(days=1)).strftime("%Y-%m-%d")+'.log'
        out_file = './../logs/MSG_'+(dt.now(tz.utc) - datetime.timedelta(days=1)).strftime("%Y-%m-%d")+'.png'
        
        warnings = {}
        errors   = {}

        f = open(log_file, 'r')
        for line in f.readlines():
            msg = Message(line)
            errors  [msg.get_process()] = errors  .get(msg.get_process(), 0) + 1 if msg.is_error()   else  errors  .get(msg.get_process(), 0)
            warnings[msg.get_process()] = warnings.get(msg.get_process(), 0) + 1 if msg.is_warning() else  warnings.get(msg.get_process(), 0)

        title = os.path.basename(f.name)        
        plot_log_statistics(errors,warnings,title,out_file)

        time.sleep(seconds_to_UTC_midnight() + 60)

        
if __name__ == '__main__':
    main()
