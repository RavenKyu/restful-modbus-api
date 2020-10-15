import functools
import json
from restful_modbus_api.utils.http_handler import CommunicationHTTP
from restful_modbus_api.utils.logger import get_logger


################################################################################
class ConfigureAPIError(Exception):
    pass


################################################################################
class API:
    ENDPOINT = ''

    # ==========================================================================
    def __init__(self, ip, port):
        logger = get_logger('http-api-handler')
        self.api = CommunicationHTTP(ip, port, logger, endpoint=self.ENDPOINT)

    # =========================================================================
    def result(f):
        @functools.wraps(f)
        def func(*args, **kwargs):
            #  커넥션 상태 처리
            ok, data, message = f(*args, **kwargs)
            if not ok:
                raise ConnectionError(str(message))
            data = json.loads(data)
            # API서버에서 주는 상태 값 처리
            return data
        return func

    def push_data(self, name, data):
        self.api.set(api=f'devices/{name}', json_data=data)
    # 데이터 저장 요청
    # =========================================================================
    def post_all_data(self):
        pass

    # =========================================================================
