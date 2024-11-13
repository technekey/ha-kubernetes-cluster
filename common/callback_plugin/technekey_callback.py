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
    CALLBACK_VERSION = 2.0
    CALLBACK_TYPE = 'notification'
    CALLBACK_NAME = 'loop_and_retry_verbose'

    def __init__(self, *args, **kwargs):
        super(CallbackModule, self).__init__(*args, **kwargs)
        self.enable_logging = False
        self.current = None
        self.task_data = OrderedDict()
        self._last_task_banner = None
        self._last_task_name = None
        self.columns = 120
        self.log_file = ""
        self.playbook_start_time = time.time()
        self.start_time_formatted = time.strftime('%Y_%m_%d_%H_%M_%S', time.localtime(self.playbook_start_time))
        self.cluster_name = None
        self.remote_virtual_env_dir = None
        self.default_username = None
        self.play_ended_early = False

    def log_to_file(self, data):
        if self.enable_logging:
            LOG_DIR = 'log'
            Path(LOG_DIR).mkdir(parents=True, exist_ok=True)
            with open(LOG_DIR + '/' + self.log_file + '_' + str(self.start_time_formatted) + '.log', "a+") as f:
                f.write(data)

    def get_screen_width(self):
        try:
            p = subprocess.Popen(['stty', 'size'], stdout=subprocess.PIPE)
            columns = p.communicate()[0].split()[-1]
        except Exception:
            columns = self.columns
        return columns

    def result_dict_init(self, task):
        self.current = task._uuid
        self.task_data[self.current] = [{'task_start_time': time.time(), 'name': task.get_name()}]
        self.log_to_file(f"[{time.ctime()}]: Starting {task.get_name()}\n")

    def result_dict_enricher(self, task_result, outcome):
        self.log_to_file(f"[{time.ctime()}]: [{task_result._host.name}]: {str(self.task_data[self.current][0]['name'])} is {outcome}\n")
        self.log_to_file(json.dumps(task_result._result, indent=2))
        self.current = task_result._task._uuid
        self.task_data[self.current].append({'hostname': task_result._host.name, 'result': outcome, 'endtime': time.time()})

    def v2_playbook_on_start(self, playbook):
        self.log_file = Path(playbook._file_name).stem

    def v2_runner_on_start(self, host, task):
        pass

    def v2_playbook_on_play_start(self, play):
        variable_manager = play.get_variable_manager()
        inventory = variable_manager._inventory

        # Retrieve all play-level variables as a dictionary
        all_vars = variable_manager.get_vars()

        # Access variables from the dictionary
        self.cluster_name = all_vars.get('cluster_name', 'unknown_cluster')
        self.remote_virtual_env_dir = all_vars.get('remote_virtual_env_dir', 'venv')  # Defaulting to 'venv' if not found

        # Debug output to confirm captured values
        self._display.display(f"Debug - cluster_name: {self.cluster_name}, remote_virtual_env_dir: {self.remote_virtual_env_dir}", color=C.COLOR_DEBUG)


    def v2_playbook_on_task_start(self, task, is_conditional):
        if task._role is not None:
            pass
        time_stamp = "[" + time.ctime() + "]"
        self._display.display(time_stamp.rjust(int(self.get_screen_width()), ' '), color=C.COLOR_OK)
        self.result_dict_init(task)

    def v2_runner_on_ok(self, result):
        self.result_dict_enricher(result, "Passed")

    def v2_runner_on_skipped(self, result):
        self.result_dict_enricher(result, "Skipped")

    def v2_runner_on_unreachable(self, result):
        self.result_dict_enricher(result, "Unreachable")

    def v2_runner_on_failed(self, result, ignore_errors=False):
        if result._task.action == "meta" and result._task.args.get('end_play'):
            self.play_ended_early = True
        self.result_dict_enricher(result, "Failed" if not ignore_errors else "Ignored")
    def v2_playbook_on_stats(self, stats):
        # Check if any hosts failed, were unreachable, or if play was ended early
        if any(stats.failures.values()) or any(stats.dark.values()) or self.play_ended_early:
            self._display.display("Playbook did not complete successfully. Skipping deployment command output.", color=C.COLOR_ERROR)
            return

        # Prepare the custom deployment message
        custom_message = (
            f"\nTo deploy the cluster, run:\n"
            f"cd {self.cluster_name}/kubespray; "
            f"source ./{self.remote_virtual_env_dir}/bin/activate; "
            f"ansible-playbook -i inventory/{self.cluster_name}/hosts.yaml --become --become-user=root "
            f"cluster.yml -u {self.default_username} --private-key ../id_ssh_rsa\n"
        )

        # Collect and display the task summary
        tracker = {}
        hosts = sorted(stats.processed.keys())
        for k, v in self.task_data.items():
            try:
                for item in v[1:]:
                    task_name = v[0]['name']
                    task_start_time = v[0]['task_start_time']
                    task_hostname = item['hostname']
                    task_result = item['result']
                    task_end_time = item['endtime']
                    task_duration = task_end_time - task_start_time
                    if task_hostname not in tracker:
                        tracker[task_hostname] = [[task_name, task_result, task_duration, task_start_time]]
                    else:
                        tracker[task_hostname].append([task_name, task_result, task_duration, task_start_time])
            except IndexError:
                continue

        # Count task failures and display task summaries
        failure_counter = 0
        for host, task_data in tracker.items():
            print(f"{Format.underline}[{host}]{Format.end}")
            for task_per_host in task_data:
                SUMMARY_COLOR = {
                    'Failed': C.COLOR_ERROR,
                    'Unreachable': C.COLOR_UNREACHABLE,
                    'Skipped': C.COLOR_SKIP,
                    'Ignored': C.COLOR_WARN,
                }.get(task_per_host[1], C.COLOR_OK)

                if task_per_host[1] == 'Failed':
                    failure_counter += 1

                formatted_line = f"{time.strftime('%H:%M:%S', time.localtime(task_per_host[3]))} {task_per_host[0]:<70.70} {task_per_host[1]:>30} {task_per_host[2]:>10.2f}s"
                self._display.display(formatted_line, color=SUMMARY_COLOR)

        # Display the custom message or error message based on failure count
        if failure_counter == 0:
            self._display.display(custom_message, color=C.COLOR_OK)
        else:
            error_message = "One or more tasks have failed; you should not proceed with kubespray installation."
            self._display.display(error_message, color=C.COLOR_ERROR)

