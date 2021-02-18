from flask import Blueprint

class CustomBlueprint(Blueprint):
    gv = dict()
    def __init__(self, name, import_name, **kwargs):
        Blueprint.__init__(self, name, import_name, **kwargs)


__all__ = ('CustomBlueprint', )