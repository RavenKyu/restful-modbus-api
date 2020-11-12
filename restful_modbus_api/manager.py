import types
import operator
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

        self.scheduler = BackgroundScheduler(timezone="Asia/Seoul")
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
            seconds, code, template, use, description = operator.itemgetter(
                'seconds', 'code', 'template', 'use', 'description'
            )(templates[key])

            comm_type = templates[key]['comm']['type']
            host, port = operator.itemgetter('host', 'port')(
                templates[key]['comm']['setting'])

            kw_argument = dict(code=code,
                               name=name,
                               interval_second=seconds,
                               template=template,
                               ip=host,
                               port=port,
                               description=description,
                               use=use,
                               comm_type=comm_type)

            self.add_job_schedule(**kw_argument)

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
                         template, ip, port, description, use, comm_type):

        module = self.get_python_module(code, name, ip, port)
        parameters = name, module, template
        comm = {'comm_typ': comm_type, 'setting': {'host': ip, 'port': port}}
        self.scheduler.pause()
        try:
            self.scheduler.add_job(
                self.request_data,
                args=parameters,
                kwargs={'code': code,
                        'use': use,
                        'description': description,
                        'comm': comm},
                id=name, trigger='interval', seconds=interval_second)
        finally:
            self.scheduler.resume()

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
            code, description, use, comm = operator.itemgetter(
                'code', 'description', 'use', 'comm')(job.kwargs)
            result.append(
                dict(id=job.id, code=code, template=template,
                     description=description, use=use, comm=comm))
        return result

