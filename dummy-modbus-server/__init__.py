import argparse
from pymodbus.server.asynchronous import StartTcpServer
from pymodbus.device import ModbusDeviceIdentification
from pymodbus.datastore import ModbusSequentialDataBlock
from pymodbus.datastore import ModbusSlaveContext, ModbusServerContext

register_data = [
    0x7765, 0x6c63, 0x6f6d, 0x6521,  # 64bit string welcome!
    0x4142, 0x4344,  # 32bit string ABCD
    0x4546,  # 16bit string EF
    0x4748,  # 8bit string G H
    0xab54, 0xa98c, 0xeb1f, 0x0ad2,  # 64bit unsigned int
    0xeedd, 0xef0b, 0x8216, 0x7eeb,  # 64bit int
    0x4996, 0x02d2,  # 32bit unsigned integer
    0xb669, 0xfd2e,  # 32bit integer
    0x3039,  # 16bit unsigned integer
    0xcfc7,  # 16bit integer
    0x7b85,  # 8bit unsigned integer, integer
    0x419d, 0x6f34, 0x540c, 0xa458,  # 64bit float
    0x4b3c, 0x614e,  # 32bit float
    0x64d2,  # 16bit float
]


def run_custom_db_server(address, port):
    # ----------------------------------------------------------------------- #
    # initialize your data store
    # ----------------------------------------------------------------------- #
    coil_block = ModbusSequentialDataBlock(1, [0] * 256)
    discrete_input_block = ModbusSequentialDataBlock(10001, [0] * 256)
    input_register_block = ModbusSequentialDataBlock(30001, register_data)
    holding_register_block = ModbusSequentialDataBlock(40001, register_data)
    store = ModbusSlaveContext(di=discrete_input_block, co=coil_block,
                               hr=holding_register_block,
                               ir=input_register_block,
                               zero_mode=True)
    context = ModbusServerContext(slaves=store, single=True)

    # ----------------------------------------------------------------------- #
    # initialize the server information
    # ----------------------------------------------------------------------- #

    identity = ModbusDeviceIdentification()
    identity.VendorName = 'pymodbus'
    identity.ProductCode = 'PM'
    identity.VendorUrl = 'http://github.com/bashwork/pymodbus/'
    identity.ProductName = 'pymodbus Server'
    identity.ModelName = 'pymodbus Server'
    identity.MajorMinorRevision = '2.3.0'

    # ----------------------------------------------------------------------- #
    # run the server you want
    # ----------------------------------------------------------------------- #

    # p = Process(target=device_writer, args=(queue,))
    # p.start()
    StartTcpServer(context, identity=identity, address=(address, port))


def arg_parser():
    parser = argparse.ArgumentParser()
    parser.add_argument('-a', '--address', type=str, default='0.0.0.0')
    parser.add_argument('-p', '--port', type=int, default=502)
    return parser
