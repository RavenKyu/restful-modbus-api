import os
import tempfile
import pytest
import requests
import mock
import yaml
import json
import pathlib
from restful_modbus_api.app import app

CURRENT_PATH = pathlib.Path(pathlib.Path(__file__).resolve()).parent
with open(str(CURRENT_PATH / pathlib.Path('sample_template.yml')), 'r') as f:
    TEMPLATE = yaml.load(f)

DUMMY_MODBUS_SERVER_ADDR = 'localhost'
DUMMY_MODBUS_SERVER_PORT = 502


###############################################################################
def ping(address, port):
    import socket
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    result = sock.connect_ex((address, port))
    if 0 == result:
        return True
    else:
        return False


###############################################################################
@pytest.fixture
def client():
    db_fd, app.config['DATABASE'] = tempfile.mkstemp()
    app.config['TESTING'] = True

    with app.test_client() as client:
        with app.app_context():
            pass
        yield client

    os.close(db_fd)
    os.unlink(app.config['DATABASE'])


###############################################################################
def test_0100_schedules(client):
    """Start with a blank schedule."""
    rv = client.get('api/v1/schedules')
    assert b'[]\n' in rv.data


###############################################################################
def test_0110_schedules(client):
    """Add a schedule"""
    url = 'api/v1/schedules'
    mimetype = 'application/json'
    headers = {
        'Content-Type': mimetype,
        'Accept': mimetype
    }
    data = TEMPLATE

    response = client.post(url, data=json.dumps(data), headers=headers)
    assert response.status_code == 200
    assert response.content_type == mimetype

    # Checking the schedules we added above are registered
    # query order by asc
    response = client.get('api/v1/schedules?sort=schedule_name:asc')
    assert response.status_code == 200
    rd = json.loads(response.data)

    assert rd[0]['schedule_name'] == 'test-1'
    assert rd[1]['schedule_name'] == 'test-2'
    assert rd[2]['schedule_name'] == 'test-3'


###############################################################################
def test_0120_schedules(client):
    # Modifying the schedule time
    url = 'api/v1/schedules'
    mimetype = 'application/json'
    headers = {
        'Content-Type': mimetype,
        'Accept': mimetype
    }
    schedule = 'test-2'
    trigger = {
        "type": "crontab",
        "setting": {'crontab': '*/10 * * * * *'}  # every 10 seconds
    }
    response = client.patch(
        f'{url}/{schedule}', data=json.dumps(trigger), headers=headers)
    assert response.status_code == 200

    response = client.get(f'{url}/{schedule}')
    assert response.status_code == 200
    rd = json.loads(response.data)
    assert rd['trigger']['type'] == trigger['type']
    assert rd['trigger']['setting'] == trigger['setting']


###############################################################################
def test_0130_schedules(client):
    # Removing a schedule
    url = 'api/v1/schedules'
    schedule = 'test-3'
    response = client.delete(f'{url}/{schedule}')
    assert response.status_code == 200

    # trying to remove a schedule job not in the scheduler
    response = client.delete(f'{url}/{schedule}')
    assert response.status_code == 404


###############################################################################
def test_0200_templates(client):
    # requesting all of templates in a schedule job
    url = 'api/v1/schedules'
    schedule = 'test-1'
    response = client.get(f'{url}/{schedule}/templates')
    assert response.status_code == 200

    rd = json.loads(response.data)
    assert 2 == len(rd)


###############################################################################
def test_0210_templates(client):
    # requesting all of templates in a schedule job
    url = 'api/v1/schedules'
    schedule = 'test-1'
    template = 'template_for_polling'
    response = client.get(f'{url}/{schedule}/templates/{template}')
    assert response.status_code == 200

    # checking the queried template is correct
    rd = json.loads(response.data)
    assert schedule == TEMPLATE[0]['schedule_name']
    assert rd == TEMPLATE[0]['templates'][template]


dummy_modbus_server = pytest.mark.skipif(
    not ping(DUMMY_MODBUS_SERVER_ADDR, DUMMY_MODBUS_SERVER_PORT),
    reason='dummy-modbus-server is not on service')


###############################################################################
@dummy_modbus_server
def test_0300_collected_data(client):
    # requesting all of the collected data by a schedule job
    url = 'api/v1/schedules'
    schedule = 'test-1'
    response_data = b'[{"data":{"data01":{"hex":"3039","note":"unsigned integer value and no scale","scale":1,"scaled_value":12345,"type":"B16_UINT","value":12345},"data02":{"hex":"03e7","note":"integer value and scale","scale":0.1,"scaled_value":99.9,"type":"B16_INT","value":999},"data03":{"hex":"cfc7","note":"integer value and no scale","scale":null,"scaled_value":-12345,"type":"B16_INT","value":-12345},"data04":{"hex":"4142","note":"string value and scale","scale":0.1,"scaled_value":"AB","type":"B16_STRING","value":"AB"}},"datetime":"2021-02-18 11:41:24","hex":"30 39 03 e7 cf c7 41 42"}]\n'
    response_data = json.loads(response_data)
    import time
    time.sleep(4)
    response = client.get(f'{url}/{schedule}/data')
    assert response.status_code == 200
    rd = json.loads(response.data)
    assert rd[0]['hex'] == response_data[0]['hex']


###############################################################################
def test_0301_collected_data_mock(mocker, client):
    # requesting all of the collected data by a schedule job
    url = 'api/v1/schedules'
    schedule = 'test-1'

    mock_client = mocker.patch.object(client, 'get', autospec=True)
    mock_res = requests.Response()
    mock_res.status_code = 200
    response_data = b'[{"data":{"data01":{"hex":"3039","note":"unsigned integer value and no scale","scale":1,"scaled_value":12345,"type":"B16_UINT","value":12345},"data02":{"hex":"03e7","note":"integer value and scale","scale":0.1,"scaled_value":99.9,"type":"B16_INT","value":999},"data03":{"hex":"cfc7","note":"integer value and no scale","scale":null,"scaled_value":-12345,"type":"B16_INT","value":-12345},"data04":{"hex":"4142","note":"string value and scale","scale":0.1,"scaled_value":"AB","type":"B16_STRING","value":"AB"}},"datetime":"2021-02-18 11:41:24","hex":"30 39 03 e7 cf c7 41 42"}]\n'
    mock_res.data = json.loads(response_data)
    mock_client.return_value = mock_res
    response = client.get(f'{url}/{schedule}')
    assert response.status_code == 200
    response_data = json.loads(response_data)
    rd = response.data
    assert rd[0]['hex'] == response_data[0]['hex']


###############################################################################
@dummy_modbus_server
def test_0302_collected_data_last_fetch(client):
    # requesting all of the collected data by a schedule job
    url = 'api/v1/schedules'
    schedule = 'test-1'
    response_data = "30 39 03 e7 cf c7 41 42"
    import time
    time.sleep(4)
    response = client.get(f'{url}/{schedule}/data?last_fetch')
    assert response.status_code == 200
    rd = json.loads(response.data)
    assert rd['hex'] == response_data

###############################################################################
@dummy_modbus_server
def test_0400_on_demend_run(client):
    url = 'api/v1/schedules'
    schedule = 'test-1'
    template = 'template_for_polling'
    mimetype = 'application/json'
    headers = {
        'Content-Type': mimetype,
        'Accept': mimetype
    }
    data = {
        "arguments": {
            "abc": 2,
        }
    }
    expect_data = '30 39 00 02 cf c7 41 42'
    response = client.post(f'{url}/{schedule}/templates/{template}/on-demand-run',
                           data=json.dumps(data), headers=headers)
    assert response.status_code == 200
    rd = json.loads(response.data)
    assert rd['hex'] == expect_data
