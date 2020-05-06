import argparse
import sys
import re
import numpy as np
import matplotlib.pyplot as plt
import os

class message:
    
    def __init__(self, msg):
        self.msg    = msg
        self.regexp = '(\w+.\w+) \[(\w+)\]: (\w{3} \w{3} \d{2} \d{2}:\d{2}:\d{2} \d{4}) (\d+.\d+.\d+.\d+) (\w+\/*\w+) (\w+) (.*)'
        self.matches = re.split(self.regexp,msg)

        if (self.matches):
            self.valid = True
        else:
            self.valid = False
            
    def is_error(self):
        if (self.valid and self.matches[6]=='ERROR'):
            return True
        else:
            return False
    
    def is_warning(self):
        if (self.valid and self.matches[6]=='WARNING'):
            return True
        else:
            return False
        
    def get_process(self):
        if (self.valid):
            return self.matches[2]

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
    ax.grid(True)

    plt.title(title)
    plt.savefig(output)
    

def main(infile , outfile):
    warnings = {}
    errors   = {}

    for line in infile.readlines():
        msg = message(line)
        if (msg.valid):
            errors  [msg.get_process()] = errors  .get(msg.get_process(), 0) + 1 if msg.is_error()   else  errors  .get(msg.get_process(), 0)
            warnings[msg.get_process()] = warnings.get(msg.get_process(), 0) + 1 if msg.is_warning() else  warnings.get(msg.get_process(), 0)
        else:
            sys.exit('ERROR parsing the log file: Line does not match regular expression')
            
    title = os.path.basename(infile.name)        
    plot_log_statistics(errors,warnings,title,outfile)

    
parser = argparse.ArgumentParser(description='Script to inspect log files from the shore station.')
required = parser.add_argument_group('required arguments')
required.add_argument('-o' , '--output_file', type=str                    , required=True , help='ouput file')
required.add_argument('-i' , '--input_file' , type=argparse.FileType('r') , required=True , help='daq .log file.')
args = parser.parse_args()

if __name__ == "__main__":
   main(args.input_file , args.output_file)
