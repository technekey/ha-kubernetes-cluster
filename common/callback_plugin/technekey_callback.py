from __future__ import (absolute_import, division, print_function)
__metaclass__ = type


from ansible.plugins.callback import CallbackBase
from ansible import constants as C
from ansible.utils.color import colorize, hostcolor
from collections import OrderedDict

import subprocess
import time
import json
from pathlib import Path

DOCUMENTATION = '''
    callback: verbose_retry
    type: stdout
    short_description: 
      1. Print the stdout and stderr during until/delay/retries
      2. Print the results during the loop for each item
    description:
      - During the retry of any task, by default the task stdout and stderr are hidden from the user on the terminal.
      - To make things more transparent, we are printing the stdout and stderr to the terminal. 
    requirements:
      - python subprocess,datetime,pprint
    '''

class Format:
    end = '\033[0m'
    underline = '\033[4m'


class CallbackModule(CallbackBase):

    '''
    Callback to various ansible runner calls.
    '''

    CALLBACK_VERSION = 2.0
    CALLBACK_TYPE = 'notification'
    CALLBACK_NAME = 'loop_and_retry_verbose'

    def __init__(self, *args, **kwargs):
        # toggle this bool to enable or disable logging to file
        self.enable_logging = False
        # This will store the UUID of the task
        self.current = None
       
        #This ordered dict will store the results of all the tasks
        # with key as self.current 
        self.task_data = OrderedDict()
        self._last_task_banner = None
        self._last_task_name = None
        
        # this is default screen width, we will try to fetch it dynamically too
        self.columns = 120
        self.log_file = ""
        self.playbook_start_time = time.time()
        self.start_time_formatted = time.strftime('%Y_%m_%d_%H_%M_%S', time.localtime(self.playbook_start_time))
        super(CallbackModule, self).__init__()

    def log_to_file(self,data):
        if self.enable_logging:
            LOG_DIR='log'
            Path(LOG_DIR).mkdir(parents=True, exist_ok=True)
            f= open(LOG_DIR + '/' + self.log_file + '_' + str(self.start_time_formatted) + '.log',"a+")
            f.write(data)
            f.close()

    def get_screen_width(self):
        columns = 0
        try:
            p = subprocess.Popen(['stty', 'size'], stdout=subprocess.PIPE)
            columns = p.communicate()[0].split()[-1]
        except Exception as ex:
            columns = self.columns
        return columns


    def result_dict_init(self, task):
        """
        Collect the following:
            1. start time of the task
            2. name of the task, this is the only location
               where, the task names are templated.
        """

        # Record the start time of the current task
        self.current = task._uuid
        self.task_data[self.current] = [{'task_start_time': time.time(), 'name': task.get_name()}]
        self.log_to_file(f"[{time.ctime()}]: Starting {task.get_name()}\n")

    def result_dict_enricher(self, task_result, outcome):
        self.log_to_file(f"[{time.ctime()}]: [{task_result._host.name}]: {str(self.task_data[self.current][0]['name'])} is {outcome}\n")
        self.log_to_file(json.dumps(task_result._result,indent=2))
        self.current = task_result._task._uuid
        self.task_data[self.current].append({'hostname': task_result._host.name, 'result' :  outcome, 'endtime' : time.time()})
       
    def v2_playbook_on_start(self, playbook):
        self.log_file = Path(playbook._file_name).stem

    def v2_runner_on_start(self, host, task):
        pass

    def v2_playbook_on_task_start(self, task, is_conditional):
        if task._role is not  None:
            pass
        time_stamp = "[" + time.ctime() + "]"
        self._display.display(time_stamp.rjust(int(self.get_screen_width()), ' '), color=C.COLOR_OK)
        self.result_dict_init(task)

    def v2_runner_on_ok(self, result):
        self.result_dict_enricher(result,"Passed")
        
    def v2_runner_on_skipped(self, result):
        self.result_dict_enricher(result,"Skipped")

    def v2_runner_on_unreachable(self, result):
        self.result_dict_enricher(result,"Unreachable")

    def v2_runner_on_failed(self, result, ignore_errors=False):
        if ignore_errors:
            self.result_dict_enricher(result,"Ignored")
        else:
            self.result_dict_enricher(result,"Failed") 

 
    def v2_playbook_on_stats(self, stats):
        tracker = {}
        hosts = sorted(stats.processed.keys())
        for k,v in self.task_data.items():
            try:
                for item in v[1:]:
                    task_name = v[0]['name']
                    task_start_time = v[0]['task_start_time']

                    task_hostname = item['hostname']
                    task_result = item['result']
                    task_end_time = item['endtime']
                    task_duration = task_end_time - task_start_time
                    if task_hostname not in tracker.keys():
                        tracker[task_hostname] = [[task_name, task_result, task_duration,task_start_time]]
                    else:
                        tracker[task_hostname].append([task_name, task_result, task_duration,task_start_time])
            except IndexError:
                continue

        for host,task_data in tracker.items():
            print(f"{Format.underline}[{host}]{Format.end}")
            for task_per_host in task_data:
                if task_per_host[1] == 'Failed':
                   SUMMARY_COLOR = C.COLOR_ERROR
                elif task_per_host[1] == 'Unreachable':
                   SUMMARY_COLOR = C.COLOR_UNREACHABLE
                elif task_per_host[1] == 'Skipped':
                   SUMMARY_COLOR = C.COLOR_SKIP
                elif task_per_host[1] == 'Ignored':
                   SUMMARY_COLOR = C.COLOR_WARN
                else:
                   SUMMARY_COLOR = C.COLOR_OK
                #for fancy printing
                if len(task_per_host[0]) > 70:
                    # Timestamp task_name task_result task_duration
                    self._display.display(f"{time.strftime('%H:%M:%S', time.localtime(task_per_host[3]))} {task_per_host[0]:<70.70}... {task_per_host[1]:>27.30} {task_per_host[2]:>10.2f}s",
                        color=SUMMARY_COLOR)
                else:
                    self._display.display(f"{time.strftime('%H:%M:%S', time.localtime(task_per_host[3]))} {task_per_host[0]:<70.70} {task_per_host[1]:>30} {task_per_host[2]:>10.2f}s",
                        color=SUMMARY_COLOR)
