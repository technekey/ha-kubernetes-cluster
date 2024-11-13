from ansible.plugins.action import ActionBase
import sys

class ActionModule(ActionBase):
    def run(self, tmp=None, task_vars=None):
        # Get the allow_virtual_env argument from the task
        allow_virtual_env = self._task.args.get('allow_virtual_env', True)

        # Determine if running in a virtual environment
        virtual_env_active = sys.prefix != sys.base_prefix

        # Print messages based on whether a virtual environment is active
        if virtual_env_active:
            message = "A virtual environment is active"
        else:
            message = "No virtual environment is active."

        # Fail or proceed based on allow_virtual_env and the virtual_env_active flag
        if virtual_env_active and not allow_virtual_env:
            return {
                'failed': True,
                'msg': f"{message}, likely the one needed for kubespray. Run 'deactivate' to run this playbook. If you think this failure is by mistake then set 'local_virtual_env_allowed' to 'True' in the hostvars."
            }
        else:
            # Proceed and print the status message
            return {
                'changed': False,
                'msg': message if allow_virtual_env else f"{message} Proceeding as allowed."
            }

