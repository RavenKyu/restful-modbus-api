from setuptools import setup, find_packages

__version__ = '0.9.0'

LONG_DESCRIPTION = open("README.md", "r", encoding="utf-8").read()

tests_require = [
    'pytest',
    'pytest-mock',
]

setup(
    name="restful-modbus-api",
    version=__version__,
    author="Duk Kyu Lim",
    author_email="hong18s@gmail.com",
    long_description=LONG_DESCRIPTION,
    long_description_content_type="text/markdown",
    description='Restful MODBUS API',
    url="https://github.com/RavenKyu/restful_modbus_api",
    license="MIT",
    keywords=["restful", "modbus", "api"],
    install_requires=[
        'flask',
        'pymodbus',
        'PyYaml',
        'apscheduler',
    ],
    tests_require=tests_require,
    packages=find_packages(
        exclude=['dummy-modbus-server', 'dummy-modubs-server.*',
                 'tests', 'tests.*']),
    package_data={},
    classifiers=[
        "Development Status :: 4 - Beta",
        "Environment :: Console",
        "Operating System :: MacOS",
        "Operating System :: Microsoft :: Windows",
        "Operating System :: POSIX :: Linux",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Topic :: Utilities",
        "License :: OSI Approved :: MIT License",
    ],
    entry_points={
        'console_scripts': [
            'restful-modbus-api=restful_modbus_api.__main__:main',
        ],
    },
    zip_safe=False,
)
