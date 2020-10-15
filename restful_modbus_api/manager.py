import types
import time
import yaml
from collections import deque
from apscheduler.schedulers.background import BackgroundScheduler

from restful_modbus_api.utils.logger import get_logger
from restful_modbus_api.modbus_handler import *
from restful_modbus_api.modbus_handler.arugment_parser import run as \
    modbus_client


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
            self.add_job_schedule(code, name, seconds, template)


    # =========================================================================
    @staticmethod
    def get_python_module(code, name):
        module = types.ModuleType(name)
        exec(code, module.__dict__)
        module.run = modbus_client
        return module

    # =========================================================================
    def add_job_schedule(self, code: str, name: str, interval_second: int,
                         template):
        module = self.get_python_module(code, name)
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
        data = module.main()
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

    # =========================================================================
    def routine(self):
        # 설정 정보 가져오기
        # 설정 정보를 이용하여 Process 생성
        while len(self.queue):
            time.sleep(0.1)
            try:
                d = self.queue.pop()
                self.api.push_data(*d)
            except Exception as e:
                self.logger.exception(str(e))
                continue
            finally:
                pass
        return

