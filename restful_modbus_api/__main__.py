import argparse
from restful_modbus_api.api.app import app
from restful_modbus_api.api.app import collector


def argument_parser():
    parser = argparse.ArgumentParser('restful-modbus-api')
    parser.add_argument('-a', '--address', default='localhost',
                        help='host address')
    parser.add_argument('-p', '--port', type=int, default=5000,
                        help='port')
    parser.add_argument('-d', '--debug', action='store_true')
    parser.add_argument('-t', '--template_file', type=str, action='append')
    return parser


def main():
    parser = argument_parser()
    argspec = parser.parse_args()

    if argspec.template_file:
        for t in argspec.template_file:
            collector.add_job_schedule_by_template_file(t)
    app.run(host=argspec.address,
            port=argspec.port,
            debug=argspec.debug)


if __name__ == '__main__':
    main()
