import unittest
import datetime
from restful_modbus_api.database.model import *
from restful_modbus_api.database import Base, db_session, engine

from restful_modbus_api.manager import Collector

FIELDS = [
    {
        'field_name': 'temperature1',
        'type': FiledType.FLOAT,
        'options': {},
        'is_field': True,

    },
    {
        'field_name': 'temperature2',
        'type': FiledType.FLOAT,
        'options': {},
        'is_field': True,
    }
]

FIELDS_2 = [
    {
        'field_name': 'humidity',
        'type': FiledType.FLOAT,
        'options': {},
        'is_field': True,

    },
    {
        'field_name': 'air_pressure',
        'type': FiledType.FLOAT,
        'options': {},
        'is_field': True,
    }
]


class MyTestCase(unittest.TestCase):
    def setUp(self):
        self.engine = engine
        # self.engine = create_engine(f'sqlite:///:memory:')
        # session = scoped_session(
        #     sessionmaker(autocommit=False,
        #                  autoflush=False,
        #                  bind=self.engine))

        self.session = db_session
        # self.session = session()

    def test_create_members(self):
        print(create_members(FIELDS))
        self.assertEqual(True, True)

    def test_create_model(self):
        test = get_model('Test', FIELDS)
        Base.metadata.create_all(bind=self.engine)
        t = test(datetime.datetime(2020, 8, 15, 00, 00, 00), 23, 22)
        self.session.add(t)
        self.session.commit()
        print(t.as_dict())
        print(self.session.query(test).one())


class TestModbusHandler(unittest.TestCase):
    def test1000_collector(self):
        code = """def main():
        v = run('read_holding_register --count 4 --ip localhost')
        # x = run('read_coils --count 16 --ip localhost')
        return v
            """
        collector = Collector()
        m = collector.get_python_module(code, 'test')
        print(m.main())

    def test1010_request_data(self):
        code = """def main():
                a = run('read_holding_register --address 40010 --count 2 --ip localhost')
                b = run('read_holding_register --address 40012 --count 2 --ip localhost')
                return a+b
                    """
        TEMPLATE = [
            {'field_name': 'temperature1',
             'type': 'B32_FLOAT',
             'options': {},
             'is_field': True, },

            {'field_name': 'temperature2',
             'type': 'B32_FLOAT',
             'options': {},
             'is_field': True, },
        ]
        collector = Collector()
        module = collector.get_python_module(code, 'test')
        print(collector.request_data('test', module, TEMPLATE))
