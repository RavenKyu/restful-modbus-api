import types
import time
import yaml
from collections import deque
from apscheduler.schedulers.background import BackgroundScheduler

from restful_modbus_api.utils.logger import get_logger
from restful_modbus_api.modbus_handler import get_json_data_with_template

CONTEXT = '''
from restful_modbus_api.modbus_handler import ModbusClient

def _main():
    with ModbusClient('{ip}', {port}) as client:
        read_input_registers = client.read_input_registers
        read_holding_registers = client.read_holding_registers
        read_discrete_inputs = client.read_discrete_inputs
        read_coils = client.read_coils
        write_single_coil = client.write_single_coil
        write_multiple_coils = client.write_multiple_coils
        write_single_register = client.write_single_register
        write_multiple_registers = client.write_multiple_registers
    
{code}
    return main()    
'''


###############################################################################
class ExceptionResponse(Exception):
    pass


###############################################################################
class Collector:
    def __init__(self):
        self.logger = get_logger('collector')
        self.device_info = None
        self.job_order_queue = None

        self.scheduler = BackgroundScheduler()
        self.scheduler.start()

        self.data = dict()
        self.data['__last_fetch'] = dict()
        self.queue = deque(maxlen=60)

    # =========================================================================
    def add_job_schedule_by_template_file(self, file_path):
        with open(file_path, 'r') as f:
            templates = yaml.safe_load(f)
        for key in templates:
            name = key
            seconds = templates[key]['seconds']
            code = templates[key]['code']
            template = templates[key]['template']

            ip = templates[key]['comm']['setting']['host']
            port = templates[key]['comm']['setting']['port']
            self.add_job_schedule(code, name, seconds, template, ip, port)

    # =========================================================================
    @staticmethod
    def get_python_module(code, name, ip, port):
        def indent(text, amount, ch=' '):
            import textwrap
            return textwrap.indent(text, amount * ch)

        code = CONTEXT.format(ip=ip, port=port, code=indent(code, 4))
        module = types.ModuleType(name)
        exec(code, module.__dict__)
        return module

    # =========================================================================
    def add_job_schedule(self, code: str, name: str, interval_second: int,
                         template, ip, port):
        module = self.get_python_module(code, name, ip, port)
        parameters = name, module, template

        self.scheduler.add_job(
            self.request_data, args=parameters, kwargs={'code': code},
            id=name, trigger='interval', seconds=interval_second)

    # =========================================================================
    def remove_job_schedule(self, _id: str):
        self.scheduler.remove_job(_id)
        del self.data[_id]
        return

    # =========================================================================
    def modify_job_schedule(self, _id, seconds):
        self.scheduler.reschedule_job(_id, trigger='interval', seconds=seconds)

    # =========================================================================
    def request_data(self, name, module, template, **kwargs):
        data = module._main()
        result = get_json_data_with_template(data, template=template)
        result['hex'] = data.hex(' ')

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
            _, _, template = job.args
            code = job.kwargs['code']
            result.append(
                dict(id=job.id, code=code, template=template))
        return result

