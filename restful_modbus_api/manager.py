import types
import operator
import yaml
import time
from collections import deque
from apscheduler.schedulers.background import BackgroundScheduler

from restful_modbus_api.utils.logger import get_logger
from restful_modbus_api.modbus_handler import get_json_data_with_template

CONTEXT = '''
from restful_modbus_api.modbus_handler import ModbusClient

def _main():
    with ModbusClient('{comm[setting][host]}', 
                       {comm[setting][port]}, 
                       '{comm[type]}') as client:
                       
        read_input_registers = client.read_input_registers
        read_holding_registers = client.read_holding_registers
        read_discrete_inputs = client.read_discrete_inputs
        read_coils = client.read_coils
        write_single_coil = client.write_single_coil
        write_multiple_coils = client.write_multiple_coils
        write_single_register = client.write_single_register
        write_multiple_registers = client.write_multiple_registers
        
        kwargs = {kwargs}
{code}
    return main()    
'''


###############################################################################
class ExceptionResponse(Exception):
    pass


###############################################################################
class ExceptionTemplateNotFound(Exception):
    pass


###############################################################################
class ExceptionScheduleNotFound(Exception):
    pass

###############################################################################
class ExceptionScheduleReduplicated(Exception):
    pass

###############################################################################
class Collector:
    def __init__(self):
        self.logger = get_logger('collector')
        self.device_info = None
        self.job_order_queue = None

        self.scheduler = BackgroundScheduler(timezone="Asia/Seoul")
        self.scheduler.start()

        self.templates = dict()

        self.data = dict()
        self.data['__last_fetch'] = dict()
        self.queue = deque(maxlen=60)

    # =========================================================================
    def wait_until(self, name, timeout, period=0.25, *args, **kwargs):
        must_end = time.time() + timeout
        while time.time() < must_end:
            if name not in self.scheduler._executors['default']._instances:
                return True
        time.sleep(period)
        return False

    # =========================================================================
    def add_job_schedule_by_template_file(self, file_path):
        with open(file_path, 'r') as f:
            data = yaml.safe_load(f)

        for key in data:
            self.templates[key] = data[key]
            trigger_type = data[key]['trigger']['type']
            trigger_setting = data[key]['trigger']['setting']
            self.add_job_schedule(key, trigger_type, trigger_setting)

    # =========================================================================
    def add_job_schedule_by_api(self, schedule_data):
        schedule_name, trigger = operator.itemgetter(
            'schedule_name', 'trigger')(schedule_data)
        schedule_names = [x['schedule_name'] for x in self.get_schedule_jobs()]
        if schedule_name in schedule_names:
            msg = f'The schedule name \'{schedule_name}\' is already assigned.'
            self.logger.error(msg)
            raise ExceptionScheduleReduplicated(msg)

        self.templates[schedule_name] = schedule_data
        self.templates[schedule_name]['templates'] = dict()
        self.add_job_schedule(
            schedule_name,
            trigger_type=trigger['type'], trigger_setting=trigger['setting'])

    # =========================================================================
    @staticmethod
    def get_python_module(code, name, comm, kwargs):
        def indent(text, amount, ch=' '):
            import textwrap
            return textwrap.indent(text, amount * ch)

        code = CONTEXT.format(comm=comm, code=indent(code, 4), kwargs=kwargs)
        module = types.ModuleType(name)
        exec(code, module.__dict__)
        return module

    # =========================================================================
    def add_job_schedule(self, key, trigger_type, trigger_setting):
        arguments = dict(
            func=self.request_data,
            args=(key,),
            id=key,
            trigger=trigger_type)
        arguments = {**arguments, **trigger_setting}

        self.scheduler.pause()
        try:
            self.scheduler.add_job(**arguments)
        finally:
            self.scheduler.resume()

    # =========================================================================
    def remove_job_schedule(self, _id: str):
        self.scheduler.remove_job(_id)
        del self.data[_id]
        return

    # =========================================================================
    def modify_job_schedule(self, _id, trigger_type, trigger_args):
        self.scheduler.reschedule_job(
            _id, trigger=trigger_type, **trigger_args)

    # =========================================================================
    def execute_script(self, schedule_name, template_name, **kwargs):
        (comm, templates) = operator.itemgetter(
            'comm', 'templates')(self.templates[schedule_name])
        (code, template) = operator.itemgetter(
            'code', 'template')(templates[template_name])
        module = Collector.get_python_module(
            code, schedule_name, comm, kwargs)

        data = module._main()
        result = get_json_data_with_template(data, template=template)
        result['hex'] = data.hex(' ')
        return result

    # =========================================================================
    def request_data(self, name):
        if name not in self.templates:
            self.logger.warning(
                f'{name} is not in the template store. '
                f'add template of \'{name}\'')
            return

        if not self.templates[name]['default_template']:
            self.logger.warning(f'\'default template\' is not set for {name}')
            return

        if not self.templates[name]['templates']:
            self.logger.warning(f'no template to run ... '
                                f'please add template first')

        (comm, templates, template_name) = operator.itemgetter(
            'comm', 'templates', 'default_template')(self.templates[name])

        result = self.execute_script(name, template_name)

        if name not in self.data:
            self.data[name] = deque(maxlen=60)
        self.data['__last_fetch'][name] = [result]
        self.data[name].append(result)
        self.data[name].rotate()
        return result

    # =========================================================================
    def get_schedule_jobs(self):
        jobs = self.scheduler.get_jobs()
        if not jobs:
            return jobs
        result = list()
        for job in jobs:
            schedule_name = job.id
            next_run_time = job.next_run_time
            template_data = self.templates[schedule_name]
            trigger, comm, description = operator.itemgetter(
                'trigger', 'comm', 'description'
            )(template_data)
            result.append(
                dict(schedule_name=schedule_name,
                     next_run_time=next_run_time,
                     description=description,
                     comm=comm,
                     trigger=trigger))
        return result

    # =========================================================================
    def execute_script_after_finishing(self, value, timeout=3):
        """
        execute script after finishing script running now
        :return:
        """
        schedule_name, template_name, arguments = operator.itemgetter(
            'schedule_name',
            'template_name',
            'arguments')(value)
        if schedule_name not in [x.id for x in self.scheduler.get_jobs()]:
            raise ExceptionScheduleNotFound(
                f'The job \'{schedule_name}\' is not found')
        job = self.scheduler.get_job(schedule_name)
        try:
            job.pause()
            if not self.wait_until(schedule_name, timeout=timeout):
                raise TimeoutError(
                    'Timeout. '
                    'We waited enough for stopping the script running now ...')

            result = self.execute_script(
                schedule_name, template_name, **arguments)
        finally:
            job.resume()
        return result
