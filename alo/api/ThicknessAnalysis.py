from flask_restful import Resource, reqparse
from flask import json
from . import api
# from ..controller.ThicknessController import ComputeThicknessData
from ..controller.ThicknessController import ComputeThicknessData

parser = reqparse.RequestParser(trim=True, bundle_errors=True)


class ThicknessAnalysisApi(Resource):
    '''
    getFlag
    '''

    def post(self, plate_limit, day_limit, hour_limit):
        # res = ComputeThicknessData(parser, plate_limit, day_limit, hour_limit)
        res = ComputeThicknessData(parser, plate_limit, day_limit, hour_limit)
        data = res.printData
        return data, 200, {'Access-Control-Allow-Origin': '*'}


api.add_resource(ThicknessAnalysisApi, '/v1.0/ThicknessAnalysisApi/<plate_limit>/<day_limit>/<hour_limit>/')
