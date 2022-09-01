from __future__ import absolute_import, division, print_function

__metaclass__ = type

import json
import os
import sys
import time
import signal

from ansible.plugins.action import ActionBase
from ansible.utils.vars import merge_hash

try:
    from __main__ import display
except ImportError:
    from ansible.utils.display import Display
    display = Display()

class TimeoutError(Exception):
    pass

def _sig_alarm(sig, tb):
    raise TimeoutError("timeout")

class ActionModule(ActionBase):
   
    # Colours
    pure_red = "\033[0;31m"
    dark_green = "\033[0;32m"
    bold = "\033[1m"
    underline = "\033[4m"
    italic = "\033[3m"
    darken = "\033[2m"
    reset_colour = '\033[0m'

    #by default colored prompt is disabled
    colored_enabled = True
    #user should provide these values 
    user_input_args = ['prompt','passing_response','abort_response','timeout']

    #these are the default values
    default_prompt = "Do you want to continue with the playbook execution?"
    default_passing_response = ['y','Y','yes','YES']
    default_abort_response = ['n','N','no','NO']
    default_timeout = 300
        
    BYPASS_HOST_LOOP = True

    def run(self, tmp=None, task_vars=None):
        if task_vars is None:
            task_vars = dict()

        for arg in self._task.args:
            if arg not in self.user_input_args:
                return {"failed": True, "msg": f"{arg} is not a valid option in user_prompt"}
        
        #if the user has not provided prompt, fallback to default prompt
        if self._task.args.get('prompt') == None:
            prompt = self.default_prompt
        else:
            prompt = self._task.args.get('prompt')
     
        # if the user has not provided the passing responses, fallback to default passing responses
        if self._task.args.get('passing_response') == None:
            passing_response = self.default_passing_response
        else:
            # the input for passing_response must be a list
            if not isinstance(self._task.args.get('passing_response'),  list):
                return {"failed": True, "msg": f"passing_response must be a list(passed value if of type {str(type(self._task.args.get('passing_response')))} )"}
            # there must be at least one element in the list
            if len(self._task.args.get('passing_response')) <= 0:
                return {"failed": True, "msg": f"passing_response must be a list with at least on element."}

            passing_response = self._task.args.get('passing_response')

        # if the user has not provided the abort responses, fallback to default abort responses
        if self._task.args.get('abort_response') == None:
            abort_response = self.default_abort_response
        else:
            # the input for abort_response must be a list
            if not isinstance(self._task.args.get('abort_response'),  list):
                return {"failed": True, "msg": f"abort_response must be a list(passed value if of type {str(type(self._task.args.get('abort_response')))} )"}
            # there must be at least one element in the list
            if len(self._task.args.get('abort_response')) <= 0:
                return {"failed": True, "msg": f"abort_response must be a list with at least on element."}

            abort_response = self._task.args.get('abort_response')

        # if the user has not provided the timeout, fallback to default timeout
        if self._task.args.get('timeout') == None:
            timeout = self.default_timeout
        else:
           #ensure that the value of timeout is an integer.
           try:
               timeout = self._task.args.get('timeout')
               int(timeout)
           except ValueError:
               return {"failed": True, "msg": f"The provided timeout value must be an integer, user provided {self._task.args.get('timeout')}"}

        result = super(ActionModule, self).run(tmp, task_vars)
        #set the default values
        result.update(
            dict(
                changed=False,
                failed=False,
                msg='',
                skipped=False
            )
        )        

        #this is done to prevent EOF error while reading from stdin
        sys.stdin = open("/dev/tty")
        signal.signal(signal.SIGALRM, _sig_alarm)
        try:
            signal.alarm(timeout)
            while True:
                ANSIBLE_FORCE_COLOR=True
                if self.colored_enabled:
                    user_response = input(f'{self.dark_green}{prompt} {passing_response} {abort_response}\r\n[Enter your response]:{self.reset_colour}')
                else:
                    user_response = input(f'{prompt} {passing_response} {abort_response}\r\n[Enter your response]:')
                if user_response in passing_response:

                    return {"failed": False, "msg": f"Prompt response passed"}
                    
                elif user_response in abort_response:
                    return {"failed": True, "msg": "User selected to abort."}
                else:
                    if self.colored_enabled:
                        print(f'{self.pure_red}Invalid response!, expecting one from {str(passing_response)} or {str(abort_response)}{self.reset_colour}')
                    else:
                        print(f'Invalid response!, expecting one from {str(passing_response)} or {str(abort_response)}')

        except TimeoutError:
            return {"failed": True, "msg": f"TimeoutError happened waiting for user response, waited {timeout} seconds"}
            pass
