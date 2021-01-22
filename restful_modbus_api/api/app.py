import json
from functools import wraps
from collections import deque
from flask import Flask, request, jsonify
from flask_restx import Resource, Api, reqparse

from werkzeug.exceptions import (BadRequest, NotFound)
from restful_modbus_api.utils.logger import get_logger
from restful_modbus_api.manager import Collector
from restful_modbus_api.manager import (
    ExceptionResponse,
    ExceptionScheduleReduplicated
)

app = Flask(__name__)
api = Api(app)

logger = get_logger('API')

collector = Collector()


###############################################################################
def result(f):
    @wraps(f)
    def func(*args, **kwargs):
        try:
            r = f(*args, **kwargs)
            return jsonify(r)
        except ExceptionScheduleReduplicated as e:
            api.abort(400, str(e))
        except NotFound as e:
            api.abort(404, str(e))
        except Exception as e:
            logger.exception(msg=str(e), exc_info=e)
            raise

    return func


###############################################################################
def get_column_names(model):
    columns = [str(x) for x in model.__table__.columns]
    columns = [x[x.rfind('.') + 1:] for x in columns]
    return columns


###############################################################################
@api.route('/schedules')
class Schedules(Resource):
    @result
    def post(self):
        d = request.get_json(force=True)
        collector.add_job_schedule_by_api(d)
        return None

    @result
    def get(self):
        return collector.get_schedule_jobs()


###############################################################################
schedule_id_parser = reqparse.RequestParser()
schedule_id_parser.add_argument(
    'seconds', type=int, help="interval time", store_missing=False)


@api.route('/schedules/<string:schedule_name>')
class SchedulesDetail(Resource):
    @result
    def delete(self, schedule_name):
        if schedule_name not in [x['id'] for x in collector.get_schedule_jobs()]:
            logger.error(f'{schedule_name} is not in the scheduler.')
            return
        return collector.remove_job_schedule(schedule_name)

    def patch(self, schedule_name):
        if schedule_name not in [x['id'] for x in collector.get_schedule_jobs()]:
            logger.error(f'{schedule_name} is not in the scheduler.')
            return

        args = schedule_id_parser.parse_args()
        collector.modify_job_schedule(
            schedule_name, args['trigger'], args['trigger_args'])
        return


###############################################################################
schedule_name_parser = reqparse.RequestParser()
schedule_name_parser.add_argument(
    'last_fetch', action='store', help="interval time")


@api.route('/schedules/<string:schedule_name>/data')
class ScheduleData(Resource):
    @result
    def post(self, schedule_name):
        d = request.get_json(force=True)
        d = json.loads(d)
        if schedule_name not in collector.data:
            collector.data[schedule_name] = deque(maxlen=60)
        collector.data[schedule_name].append(d)
        return None

    @result
    def get(self, schedule_name):
        args = schedule_name_parser.parse_args()
        if schedule_name not in collector.data['__last_fetch'] or \
                schedule_name not in collector.data:
            raise NotFound(
                f'No data for {schedule_name}. '
                f'may not be collecting the data now.')
        if args['last_fetch'] is not None:
            data = collector.data['__last_fetch'][schedule_name]
            return data.pop() if data else None
        return list(collector.data[schedule_name])

    @result
    def delete(self, schedule_name):
        print(schedule_name)


###############################################################################
@api.route('/schedules/<string:schedule_name>/data/<int:index>')
class ScheduleDataIndex(Resource):
    @result
    def get(self, schedule_name, index):
        return list(collector.data[schedule_name])[index]


###############################################################################
@api.route('/procedure_call')
class RunDeviceProcedureCall(Resource):
    @result
    def post(self):
        d = request.get_json(force=True)
        data = collector.execute_script_after_finishing(d)
        return data
