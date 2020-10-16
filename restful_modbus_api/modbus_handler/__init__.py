import signal
import yaml
import socket
import enum
import struct
import json
import datetime
import functools

from pymodbus.pdu import ModbusExceptions
from pymodbus.client.sync import ModbusTcpClient as _ModbusClient
from pymodbus.payload import BinaryPayloadBuilder, BinaryPayloadDecoder
from pymodbus.constants import Endian
from pymodbus import exceptions
from restful_modbus_api.modbus_handler.arugment_parser import \
    argument_parser


###############################################################################
class ModbusClient(_ModbusClient):
    def __init__(self, host, port, verbose=0):
        _ModbusClient.__init__(self, host=host, por=port)

    # =========================================================================
    def response_handle(f):
        @functools.wraps(f)
        def func(*args, **kwargs):
            response = f(*args, **kwargs)
            data = response.encode()
            if 1 == len(data):
                raise ExceptionResponse(
                    ModbusExceptions.decode(int.from_bytes(data, 'big')))
            return data[1:]

        return func

    # =========================================================================
    def error_handle(f):
        @functools.wraps(f)
        def func(*args, **kwargs):
            try:
                return f(*args, **kwargs)
            except exceptions.ConnectionException as e:
                print('** Error: ', e)
            except ExceptionResponse as e:
                print('** Error: ', e)
            except Exception:
                import traceback
                traceback.print_exc()
                return

        return func

    # =========================================================================
    @error_handle
    @response_handle
    def read_input_registers(self, command):
        parser = argument_parser()
        command = 'read_input_register ' + command
        spec = parser.parse_args(command.split())
        response = _ModbusClient.read_input_registers(
            self, spec.address, spec.count)
        return response

    # =========================================================================
    @error_handle
    @response_handle
    def read_holding_registers(self, command):
        parser = argument_parser()
        command = 'read_holding_register ' + command
        spec = parser.parse_args(command.split())
        response = _ModbusClient.read_input_registers(
            self, spec.address, spec.count)
        return response

    # =========================================================================
    @error_handle
    @response_handle
    def read_discrete_inputs(self, command):
        parser = argument_parser()
        command = 'read_discrete_inputs ' + command
        spec = parser.parse_args(command.split())
        response = _ModbusClient.read_discrete_inputs(
            self, spec.address, spec.count)
        return response

    # =========================================================================
    @error_handle
    @response_handle
    def read_coils(self, command):
        parser = argument_parser()
        command = 'read_coils ' + command
        spec = parser.parse_args(command.split())
        response = _ModbusClient.read_coils(
            self, spec.address, spec.count)
        return response

    # =========================================================================
    @error_handle
    @response_handle
    def write_single_coil(self, command):
        parser = argument_parser()
        command = 'write_single_coil ' + command
        spec = parser.parse_args(command.split())
        response = _ModbusClient.write_coil(
            self, spec.address, spec.value)
        return response

    # =========================================================================
    @error_handle
    @response_handle
    def write_multiple_coils(self, command):
        parser = argument_parser()
        command = 'write_multiple_coils ' + command
        spec = parser.parse_args(command.split())
        response = _ModbusClient.write_coils(
            self, spec.address, list(map(int, spec.values)))
        return response

    # =========================================================================
    @error_handle
    @response_handle
    def write_single_register(self, command):
        parser = argument_parser()
        command = 'write_single_register ' + command
        spec = parser.parse_args(command.split())
        builder = BinaryPayloadBuilder(byteorder=Endian.Big,
                                       wordorder=Endian.Big)
        for func, value in spec.values[:1]:
            getattr(builder, func)(value)
        payload = builder.build()

        response = _ModbusClient.write_register(
            self,
            spec.address, payload[0],
            skip_encode=True,
            unit=spec.unit_id)

        return response

    # =========================================================================
    @error_handle
    @response_handle
    def write_multiple_registers(self, command):
        parser = argument_parser()
        command = 'write_multiple_registers ' + command
        spec = parser.parse_args(command.split())

        builder = BinaryPayloadBuilder(byteorder=Endian.Big,
                                       wordorder=Endian.Big)
        for func, value in spec.values:
            getattr(builder, func)(value)
        payload = builder.build()

        response = _ModbusClient.write_registers(
            self, spec.address, payload, skip_encode=True,  unit=spec.unit_id)
        return response


###############################################################################
class ExceptionResponse(Exception):
    pass


###############################################################################
class DataType(enum.Enum):
    BIT1_BOOLEAN = {'name': '1b boolean', 'length': 1, 'format': '?'}
    BIT8 = {'name': '8 bits bool', 'length': 1, 'format': '>B'}

    B8_UINT = {'name': '8b uint', 'length': 1, 'format': '>B'}
    B8_INT = {'name': '8b int', 'length': 1, 'format': '>b'}
    B16_UINT = {'name': '16b uint', 'length': 2, 'format': '>H'}
    B16_INT = {'name': '16b int', 'length': 2, 'format': '>h'}
    B32_UINT = {'name': '32b uint', 'length': 4, 'format': '>I'}
    B32_INT = {'name': '32b int', 'length': 4, 'format': '>i'}
    B64_UINT = {'name': '64b uint', 'length': 8, 'format': '>Q'}
    B64_INT = {'name': '64b int', 'length': 8, 'format': '>q'}

    B16_FLOAT = {'name': '16b float', 'length': 2, 'format': '>e'}
    B32_FLOAT = {'name': '32b float', 'length': 4, 'format': '>f'}
    B64_FLOAT = {'name': '64b float', 'length': 8, 'format': '>d'}

    B8_STRING = {'name': '8b sting', 'length': 1, 'format': '>c'}
    B16_STRING = {'name': '16b sting', 'length': 2, 'format': '>cc'}
    B32_STRING = {'name': '32b sting', 'length': 4, 'format': '>cccc'}
    B64_STRING = {'name': '64b sting', 'length': 8, 'format': '>cccccccc'}


###############################################################################
def get_template(name):
    if not name:
        return None
    try:
        with open('templates.yml', 'r') as f:
            return yaml.safe_load(f)[name]
    except FileNotFoundError:
        print('\n** Error: Template file templates.yml should be '
              'in the directory where modbusclc executed.')
        return None
    except KeyError:
        print(f'\n** Error: {name} is not in the template. Please Check it ..')
        return None
    except Exception:
        import traceback
        traceback.print_exc()
        return None


###############################################################################
def get_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(('10.255.255.255', 1))
        ip = s.getsockname()[0]
    except Exception:
        ip = '127.0.0.1'
    finally:
        s.close()
    return ip


###############################################################################
def chunks(lst, size_list: (list, tuple), register_size=2):
    """

    :param lst: b'\xfc\x19\xff\xff\xff\xfe'
    :param size_list: (2, 2, 1, 1)
    :param register_size: 2 (16bit)
    :return: [('fc19', 1), ('ffff', 2), ('ff', 3), ('fe', 3)]

    """
    index = 0
    register = 0
    for i in size_list:
        hex_value = lst[index:index + i].hex()
        yield hex_value, int(register)
        register += i / register_size
        index += i


###############################################################################
def chunks_bits(lst, size_list: (list, tuple)):
    address = 0
    value = int.from_bytes(lst, 'little')
    for i, _ in enumerate(size_list):
        yield (value >> i) & 1, address
        address += 1


###############################################################################
def space(string, length):
    """

    :param string: '556e697432332d41'
    :param length: 4
    :return: 556e 6974 3233 2d41
    """
    return ' '.join(
        string[i:i + length] for i in range(0, len(string), length))


###############################################################################
def make_record(index, data, template):
    record = list()
    data_type = getattr(DataType, template['type'])
    fmt = data_type.value['format']

    record.append(data_type.name)
    if data_type is data_type.BIT1_BOOLEAN:
        record.append(data[index][0])
        d = bool(data[index][0])
    else:
        record.append(space(data[index][0], 4))
        d = struct.unpack(fmt, bytes.fromhex(data[index][0]))

    if data_type in (
            DataType.B8_STRING, DataType.B16_STRING, DataType.B32_STRING,
            DataType.B64_STRING):
        d = b''.join(d).decode('utf-8')
    elif data_type in (DataType.BIT8,):
        d = f'{d[0]:07b}'
    elif data_type in (DataType.BIT1_BOOLEAN,):
        pass
    else:
        d = d[0]
    record.append(d)
    record.append(template['note'])
    return record


###############################################################################
def get_json_data_with_template(data: bytes, template):
    n = [DataType[x['type']].value['length'] for x in template]
    data = list(chunks(data, n))
    result = dict()
    result['datetime'] = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    result['data'] = dict()
    key = ['type', 'hex', 'value', 'note']

    for i, t in enumerate(template):
        try:
            record = make_record(i, data, t)
            result['data'][t['key']] = dict(zip(key, record))
        except struct.error:
            note = 'item exists but no data'
            record = [f'{t["type"]}'] + [None] * 3 + [note]
            result['data'][t['key']] = dict(zip(key, record))
            continue

    return result


###############################################################################
def request_response_messages(command, data: bytes, address=''):
    now = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    print(f'{now} | {command:8s} | {address:15s} > {data.hex(" ")}')


###############################################################################
__all__ = ['get_json_data_with_template', ]

