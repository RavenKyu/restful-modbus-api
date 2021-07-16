import flask
import logging
import operator
from flask import request, abort, make_response
from flask import jsonify, redirect, url_for
from functools import wraps
from restful_modbus_api.modules.api import CustomBlueprint

from restful_modbus_api.manager import (
    ExceptionResponse,
    ExceptionScheduleReduplicated,
    NotFound)

bp = CustomBlueprint('api', __name__)


###############################################################################
def custom_error(message, status_code):
    msg = dict(message=message)
    return make_response(jsonify(msg), status_code)


###############################################################################
def result(f):
    @wraps(f)
    def func(*args, **kwargs):
        try:
            r = f(*args, **kwargs)
            return jsonify(r)
        except ExceptionScheduleReduplicated as e:
            return custom_error(str(e), 400)
        except NotFound as e:
            return custom_error(str(e), 404)
        except Exception as e:
            logging.exception(msg=str(e), exc_info=e)
            raise
    return func


###############################################################################
def query_data_sort(data, query: str):
    query = query.split(',')
    for q in query:
        key, order_by = q.split(':')
        order_by = {'desc': True, 'asc': False}[order_by]
        data = sorted(data, key=operator.itemgetter(key), reverse=order_by)
    return data


###############################################################################
def query_data(data, query):
    if 'sort' in query:
        data = query_data_sort(data, query['sort'])
    return data


###############################################################################
@bp.route('/schedules', methods=('GET', 'POST'))
@result
def schedules():
    # inserting a collecting schedule with json data
    if request.method == 'POST':
        d = request.get_json(force=True)
        collector = bp.gv['collector']
        collector.add_job_schedules(d)
        return None

    # requesting all of the collecting schedule with json format
    elif request.method == 'GET':
        collector = bp.gv['collector']
        value = collector.get_schedule_jobs()

        query = request.args.to_dict()
        value = query_data(value, query)
        return value


###############################################################################
@bp.route('/schedules/<string:schedule_name>',
          methods=('GET', 'DELETE', 'PATCH'))
@result
def schedule(schedule_name):
    collector = bp.gv['collector']

    # requesting all of the collecting schedule with json format
    if request.method == 'GET':
        value = collector.get_schedule_job(schedule_name)
        return value

    #  requesting to remove the job schedule
    if request.method == 'DELETE':
        collector.remove_job_schedule(schedule_name)
        return None

    # modify trigger of the schedule
    if request.method == 'PATCH':
        d = request.get_json(force=True)
        trigger, trigger_args = operator.itemgetter(
            'type', 'setting')(d)
        collector.modify_job_schedule(
            schedule_name, trigger, trigger_args)
        return None


###############################################################################
@bp.route('/schedules/<string:schedule_name>/templates', methods=('GET', ))
@result
def schedule_templates(schedule_name):
    # requesting all of the template in schedule with json format
    if request.method == 'GET':
        collector = bp.gv['collector']
        value = collector.get_templates_in_schedule(schedule_name)
        return value


###############################################################################
@bp.route('/schedules/<string:schedule_name>/templates/<string:template_name>',
          methods=('GET', ))
@result
def schedule_template(schedule_name, template_name):
    # requesting all of the template in schedule with json format
    if request.method == 'GET':
        collector = bp.gv['collector']
        template = collector.get_the_template_in_schedule(
            schedule_name, template_name)
        return template


###############################################################################
@bp.route('/schedules/<string:schedule_name>/templates/'
          '<string:template_name>/on-demand-run', methods=('POST',))
@result
def schedule_template_on_demand_run(schedule_name, template_name):
    if request.method == 'POST':
        query = request.args.to_dict()
        arguments = request.get_json(force=True)

        collector = bp.gv['collector']
        template = collector.execute_script_after_finishing(
            schedule_name, template_name, **arguments)
        return template


###############################################################################
@bp.route('/schedules/<string:schedule_name>/data', methods=('GET', ))
@result
def schedule_data(schedule_name):
    # requesting all of the template in schedule with json format
    if request.method == 'GET':
        collector = bp.gv['collector']
        query = request.args.to_dict()
        if 'last_fetch' in query:
            return collector.get_last_fetch_data(schedule_name)
        return collector.get_all_data(schedule_name)

