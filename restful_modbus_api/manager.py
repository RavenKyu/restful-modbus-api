import logging
import types
import operator
import time
from collections import deque
from apscheduler.schedulers.background import BackgroundScheduler
from restful_modbus_api.modbus_handler import get_json_data_with_template

CONTEXT = '''
from restful_modbus_api.modbus_handler import ModbusClient

def _main():
    with ModbusClient('{comm[setting][host]}', {comm[setting][port]}, '{comm[type]}') as client:
        read_input_registers = client.read_input_registers
        read_holding_registers = client.read_holding_registers
        read_discrete_inputs = client.read_discrete_inputs
        read_coils = client.read_coils
        write_single_coil = client.write_single_coil
        write_multiple_coils = client.write_multiple_coils
        write_single_register = client.write_single_register
        write_multiple_registers = client.write_multiple_registers
        
        _arguments = {kwargs}
{code}
        return main()    
'''


###############################################################################
class ExceptionResponse(Exception):
    pass


###############################################################################
class NotFound(Exception):
    pass


###############################################################################
class ExceptionScheduleReduplicated(Exception):
    pass


###############################################################################
class Collector:
    def __init__(self):
        logging.info('Collector Starting ...')

        self.device_info = None
        self.job_order_queue = None

        self.scheduler = BackgroundScheduler(timezone="Asia/Seoul")
        self.scheduler.start()

        self.templates = dict()

        self.data = dict()
        self.data['__last_fetch'] = dict()

    # =========================================================================
    def wait_until(self, name, timeout, period=0.25, *args, **kwargs):
        must_end = time.time() + timeout
        while time.time() < must_end:
            if name not in self.scheduler._executors['default']._instances:
                return True
        time.sleep(period)
        return False

    # =========================================================================
    def add_job_schedules(self, schedule_templates: list):
        logging.debug("Adding schedules with template.")
        for schedule_template in schedule_templates:
            schedule_name, trigger = operator.itemgetter(
                'schedule_name', 'trigger')(schedule_template)
            schedule_names = [x['schedule_name'] for x in
                              self.get_schedule_jobs()]
            if schedule_name in schedule_names:
                msg = f'The schedule name \'{schedule_name}\' is already assigned.'
                logging.error(msg)
                raise ExceptionScheduleReduplicated(msg)

            self.templates[schedule_name] = schedule_template
            self._add_job_schedule(
                schedule_name,
                trigger_type=trigger['type'],
                trigger_setting=trigger['setting'])
            logging.debug(
                f'Schedule "{schedule_name}" is added in the job scheduler.')

    # =========================================================================
    @staticmethod
    def get_python_module(code, name, comm, kwargs):
        def indent(text, amount, ch=' '):
            import textwrap
            return textwrap.indent(text, amount * ch)

        code = CONTEXT.format(comm=comm, code=indent(code, 8), kwargs=kwargs)
        module = types.ModuleType(name)
        exec(code, module.__dict__)
        return module, code

    # =========================================================================
    def crontab_add_second(self, crontab):
        cron = [
            'second',
            'minute',
            'hour',
            'day',
            'month',
            'day_of_week']

        crontab = crontab.split()
        if 6 != len(crontab):
            raise ValueError(
                'crontab need 6 values. '
                'second, minute, hour, day, month, day_of_week')
        value = dict(zip(cron, crontab))
        logging.debug(f'crontab input: {crontab}\t-> output: {value}')
        return value

    # =========================================================================
    def _add_job_schedule(self, key, trigger_type, trigger_setting):
        if trigger_type == 'crontab' and 'crontab' in trigger_setting:
            crontab = self.crontab_add_second(trigger_setting['crontab'])
            trigger_type = 'cron'
            trigger_setting = {**trigger_setting, **crontab}
            del trigger_setting['crontab']

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
    def remove_job_schedule(self, schedule_name: str):
        self.get_schedule_job(schedule_name)
        logging.debug(
            f'Removing the schedule "{schedule_name}" from scheduler.')
        self.scheduler.remove_job(schedule_name)

        try:
            logging.debug(f'Removing the collected data.')
            del self.data[schedule_name]
        except KeyError:
            logging.warning(
                f'Failed to find the schedule name "{schedule_name}". '
                f'It should be failing to collect data. '
                f'please check the connection is ok.')

        logging.debug(f'Removing the template "{schedule_name}" '
                      f'from the template store.')
        del self.templates[schedule_name]
        return

    # =========================================================================
    def modify_job_schedule(self, schedule_name, trigger_type, trigger_args):
        logging.debug('Modifying the job schedule "{schedule_name}".')
        if trigger_type == 'crontab' and 'crontab' in trigger_args:
            crontab = self.crontab_add_second(trigger_args['crontab'])
            trigger = 'cron'

            setting = {**trigger_args, **crontab}
            del setting['crontab']
        else:
            trigger = trigger_type
            setting = trigger_args

        job = self.scheduler.get_job(schedule_name)
        job.reschedule(trigger, **setting)
        self.templates[schedule_name]['trigger'] = dict(
            type=trigger_type, setting=trigger_args)
        logging.debug(f'leaving function ...')

    # =========================================================================
    @staticmethod
    def insert_number_each_line(data: str):
        result = list()
        data = data.split('\n')
        for (number, line) in enumerate(data):
            result.append(f'{number + 1:04} {line}')
        return '\n'.join(result)

    # =========================================================================
    def execute_script(self, schedule_name, template_name, **kwargs):
        logging.debug(f'{schedule_name}::{template_name} - '
                      f'Preparing to execute the script.')

        (comm, templates) = operator.itemgetter(
            'comm', 'templates')(self.templates[schedule_name])
        (code, template) = operator.itemgetter(
            'code', 'template')(templates[template_name])
        module, code = Collector.get_python_module(
            code, schedule_name, comm, kwargs)
        try:
            logging.debug(f'{schedule_name}::{template_name} - '
                          f'Executing the script')
            data = module._main()
        except Exception as e:
            code = Collector.insert_number_each_line(code)
            logging.error(f'{e}\ncode: \n{code}')
            raise
        result = get_json_data_with_template(data, template=template)
        result['hex'] = data.hex(' ')
        return result

    # =========================================================================
    def request_data(self, name):
        st = time.time()
        if name not in self.templates:
            logging.warning(
                f'{name} is not in the template store. '
                f'add template of \'{name}\'')
            return

        if not self.templates[name]['default_template']:
            logging.warning(f'\'default template\' is not set for {name}')
            return

        if not self.templates[name]['templates']:
            logging.warning(
                f'no template to run ... please add template first')

        (comm, templates, template_name) = operator.itemgetter(
            'comm', 'templates', 'default_template')(self.templates[name])

        result = self.execute_script(name, template_name)

        if name not in self.data:
            self.data[name] = deque(maxlen=60)
        self.data['__last_fetch'][name] = [result]
        self.data[name].append(result)
        self.data[name].rotate()
        latency_ms = int((time.time() - st) * 1000)
        logging.info(f'{name}::{template_name} - Succeed to collect data. '
                     f'- {latency_ms}ms')
        return result

    # =========================================================================
    def get_schedule_jobs(self):
        jobs = self.scheduler.get_jobs()
        if not jobs:
            logging.debug('No schedules running now.')
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
    def get_schedule_job(self, schedule_name):
        schedules = self.get_schedule_jobs()
        try:
            return next(s for s in schedules
                        if s['schedule_name'] == schedule_name)
        except StopIteration:
            raise NotFound(f'{schedule_name} is not in scheduler')

    # =========================================================================
    def get_templates_in_schedule(self, schedule_name):
        """
        return all of template in the schedule
        :param schedule_name:
        :return:
        """
        if schedule_name not in self.templates:
            raise NotFound(f'{schedule_name} is not in the schedules')
        return self.templates[schedule_name]['templates']

    # =========================================================================
    def get_the_template_in_schedule(self, schedule_name, template_name):
        """
        return the template in the schedule
        :param schedule_name
        :param template_name
        :return:
        """
        templates = self.get_templates_in_schedule(schedule_name)
        if template_name not in templates:
            raise NotFound(f'{template_name} is not in the {schedule_name}')
        return self.templates[schedule_name]['templates'][template_name]

    # =========================================================================
    def get_all_data(self, schedule_name):
        """
        return all of collected data in the queue of the schedule job
        :param schedule_name:
        :return:
        """
        if schedule_name not in self.data:
            raise NotFound(
                f'{schedule_name} is not in the data store for scheduler. or '
                f'even It may not have started the first collecting yet.')
        return list(self.data[schedule_name])

    # =========================================================================
    def get_last_fetch_data(self, schedule_name):
        """
        return all of collected data in the queue of the schedule job
        :param schedule_name:
        :return:
        """
        if schedule_name not in self.data['__last_fetch']:
            raise NotFound(
                f'{schedule_name} is not in the data store for scheduler. or '
                f'even It may not have started the first collecting yet.')
        data = self.data['__last_fetch'][schedule_name]
        return data.pop() if data else None

    # =========================================================================
    def execute_script_after_finishing(
            self, schedule_name, template_name, arguments, timeout=3):
        """
        execute script after finishing script running now
        :return:
        """
        if schedule_name not in [x.id for x in self.scheduler.get_jobs()]:
            raise NotFound(
                f'The job \'{schedule_name}\' is not found')
        job = self.scheduler.get_job(schedule_name)
        try:
            job.pause()
            logging.debug(f'The job schedule is pausing for '
                          f'running the on-demand-run. - '
                          f'{schedule_name}::{template_name}')
            if not self.wait_until(schedule_name, timeout=timeout):
                raise TimeoutError(
                    'Timeout. '
                    'We waited enough for stopping the script running now ...')

            result = self.execute_script(
                schedule_name, template_name, **arguments)
        finally:
            job.resume()
            logging.debug(f'Resumed the schedule job - {schedule_name}')
        return result
