from . import arg_parser
from . import run_custom_db_server

if __name__ == "__main__":
    args = arg_parser().parse_args()
    run_custom_db_server(args.address, args.port)
