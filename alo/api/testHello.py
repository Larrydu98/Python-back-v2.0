from flask_restful import Resource, reqparse
from flask import json
from . import api
from ..controller.getTestDataController import ComputerTestData

parser = reqparse.RequestParser(trim=True, bundle_errors=True)

class testHello(Resource):
    '''
    getFlag
    '''

    def post(self, limit):
        res = ComputerTestData(parser, limit)
        Data = res.printData()
        return Data, 200, {'Access-Control-Allow-Origin': '*'}
api.add_resource(testHello, '/v1.0/testHello/<limit>')