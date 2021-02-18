import argparse
import re
from restful_modbus_api.modbus_handler import *


###############################################################################
def regex_type_0or1(arg_value, pat=re.compile(r"^[0|1| ]*$")):
    if not pat.match(arg_value):
        raise argparse.ArgumentTypeError('The values must be 0 or 1.')
    return arg_value


###############################################################################
class ActionMultipleTypeValues(argparse.Action):
    def __init__(
            self, option_strings, dest, const,
            nargs=None,
            default=None,
            type=None,
            required=False,
            help=None,
            metavar=None):
        super(ActionMultipleTypeValues, self).__init__(
            option_strings=option_strings,
            dest=dest,
            nargs=nargs,
            const=const,
            default=default,
            type=type,
            required=required,
            help=help,
            metavar=metavar)

    @staticmethod
    def _copy_items(items):
        if items is None:
            return []
        if type(items) is list:
            return items[:]
        import copy
        return copy.copy(items)

    def __call__(self, parser, namespace, values, option_string=None):
        items = getattr(namespace, self.dest, None)
        items = ActionMultipleTypeValues._copy_items(items)
        if 'add_bits' == self.const:
            values = list(map(int, values.replace(' ', '')))
            values.reverse()

        items.append((self.const, values))
        setattr(namespace, self.dest, items)


###############################################################################
def argument_parser():
    parent_parser = argparse.ArgumentParser(add_help=False)
    parent_parser.add_argument('--ip', type=str, default='localhost')
    parent_parser.add_argument('--port', type=int, default=5000)
    parent_parser.add_argument('-t', '--template', type=str,
                               help='template name', )

    ###########################################################################
    essential_options_parser = argparse.ArgumentParser(add_help=False)
    essential_options_parser.add_argument(
        '-i', '--unit-id', type=int, default=0, help='unit id')
    essential_options_parser.add_argument(
        '-v', '--verbose', action='count')

    ###########################################################################
    single_register_data_type_parser = argparse.ArgumentParser(add_help=False)
    single_register_data_type_parser.add_argument(
        '--string', dest='values', action=ActionMultipleTypeValues,
        const='add_string', help='string ex) hello_world or "hello world"')
    single_register_data_type_parser.add_argument(
        '--b16int', dest='values', type=int, action=ActionMultipleTypeValues,
        const='add_16bit_int')
    single_register_data_type_parser.add_argument(
        '--b16uint', dest='values', type=int, action=ActionMultipleTypeValues,
        const='add_16bit_uint')
    single_register_data_type_parser.add_argument(
        '--b16float', dest='values', type=float,
        action=ActionMultipleTypeValues,
        const='add_16bit_float', help='')

    ###########################################################################
    multiple_register_data_type_parser = argparse.ArgumentParser(
        add_help=False)
    multiple_register_data_type_parser.add_argument(
        '--string', dest='values', action=ActionMultipleTypeValues,
        const='add_string', help='string ex) hello_world or "hello world"')
    multiple_register_data_type_parser.add_argument(
        '--bits', dest='values', type=regex_type_0or1,
        action=ActionMultipleTypeValues, const='add_bits',
        help='bits ex) 1110 => 00001110 or 1111000010101010 or "1111 00 11"')
    multiple_register_data_type_parser.add_argument(
        '--b8int', dest='values', type=int, action=ActionMultipleTypeValues,
        const='add_8bit_int')
    multiple_register_data_type_parser.add_argument(
        '--b8uint', dest='values', type=int, action=ActionMultipleTypeValues,
        const='add_8bit_uint')
    multiple_register_data_type_parser.add_argument(
        '--b32int', dest='values', type=int, action=ActionMultipleTypeValues,
        const='add_32bit_int', help='')
    multiple_register_data_type_parser.add_argument(
        '--b32uint', dest='values', type=int, action=ActionMultipleTypeValues,
        const='add_32bit_uint', help='')
    multiple_register_data_type_parser.add_argument(
        '--b64int', dest='values', type=int, action=ActionMultipleTypeValues,
        const='add_64bit_int', help='')
    multiple_register_data_type_parser.add_argument(
        '--b64uint', dest='values', type=int, action=ActionMultipleTypeValues,
        const='add_64bit_uint', help='')
    multiple_register_data_type_parser.add_argument(
        '--b32float', dest='values', type=float,
        action=ActionMultipleTypeValues,
        const='add_32bit_float', help='')
    multiple_register_data_type_parser.add_argument(
        '--b64float', dest='values', type=float,
        action=ActionMultipleTypeValues,
        const='add_64bit_float', help='')

    ###########################################################################
    parser = argparse.ArgumentParser(
        prog='',
        description='description',
        epilog='end of description', )

    sub_parser = parser.add_subparsers(dest='sub_parser')

    ###########################################################################
    # Read Coils 0x01
    read_coils_parser = sub_parser.add_parser(
        'read_coils', help='Read Coil(s)',
        parents=[parent_parser, essential_options_parser],
        conflict_handler='resolve')
    read_coils_parser.add_argument(
        '-a', '--address', type=int, default=1, help='address'),
    read_coils_parser.add_argument(
        '-c', '--count', type=int, default=1, help='number of coils')

    ###########################################################################
    # Read Discrete Inputs 0x02
    read_discrete_inputs_parser = sub_parser.add_parser(
        'read_discrete_inputs', help='Read Discrete Inputs',
        parents=[parent_parser, essential_options_parser],
        conflict_handler='resolve')
    read_discrete_inputs_parser.add_argument(
        '-a', '--address', type=int, default=10001, help='address'),
    read_discrete_inputs_parser.add_argument(
        '-c', '--count', type=int, default=1, help='number of coils')

    ###########################################################################
    # Read Holding Registers 0x03
    read_holding_register_parser = sub_parser.add_parser(
        'read_holding_register', help='Setting Command',
        conflict_handler='resolve',
        parents=[parent_parser, essential_options_parser])
    read_holding_register_parser.add_argument(
        '-a', '--address', type=int, default=40001, help='address'),
    read_holding_register_parser.add_argument(
        '-c', '--count', type=int, default=2, help='number of registers')

    ###########################################################################
    # Read Input Registers 0x04
    read_input_register_parser = sub_parser.add_parser(
        'read_input_register', help='Setting Command',
        conflict_handler='resolve',
        parents=[parent_parser, essential_options_parser])
    read_input_register_parser.add_argument(
        '-a', '--address', type=int, default=30001, help='address'),
    read_input_register_parser.add_argument(
        '-c', '--count', type=int, default=2, help='number of registers')

    ###########################################################################
    # Writing Single Coil 0x05
    write_single_coil_parser = sub_parser.add_parser(
        'write_single_coil', help='write single Coil',
        parents=[parent_parser, essential_options_parser],
        conflict_handler='resolve')
    write_single_coil_parser.add_argument(
        'address', type=int, help='address where the value stores')
    write_single_coil_parser.add_argument(
        'value', type=int, choices=[0, 1],
        help='1/0 boolean.')

    ###########################################################################
    # Writing Single Register 0x06
    write_single_registers_parser = sub_parser.add_parser(
        'write_single_register', help='writing single register',
        parents=[parent_parser, essential_options_parser,
                 single_register_data_type_parser],
        conflict_handler='resolve')
    write_single_registers_parser.add_argument(
        'address', type=int, help='address where the value stores')

    ###########################################################################
    # Writing Multiple Coils 0x0f
    write_single_coil_parser = sub_parser.add_parser(
        'write_multiple_coils', help='writing multiple coils',
        parents=[parent_parser, essential_options_parser],
        conflict_handler='resolve')
    write_single_coil_parser.add_argument(
        'address', type=int, help='address where the value stores')
    write_single_coil_parser.add_argument(
        'values', type=regex_type_0or1, help='1/0 boolean. ex) 01101100')

    ###########################################################################
    # Writing Multiple Register 0x10
    write_multiple_registers_parser = sub_parser.add_parser(
        'write_multiple_registers', help='writing multiple registers',
        parents=[parent_parser, essential_options_parser,
                 multiple_register_data_type_parser,
                 single_register_data_type_parser],
        conflict_handler='resolve')
    write_multiple_registers_parser.add_argument(
        'address', type=int, help='address where the value stores')

    return parser


__all__ = ['argument_parser', ]
