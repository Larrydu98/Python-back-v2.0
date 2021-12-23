import psycopg2
import json
from alo.utils import readConfig
from flask_restful import Resource, reqparse
from alo.utils import readConfig
parser = reqparse.RequestParser(trim=True, bundle_errors=True)

class GetTestData:
    @staticmethod
    def getMareyDataDB(parser,limit):
        label = ["platetype", "tgtwidth", "tgtlength", "tgtthickness"]
        post_lable = {}
        for index in label:
            parser.add_argument(index, type=str, required=True)
        args = parser.parse_args(strict=True)
        for key, value in args.items():
            if (key == 'platetype'):
                test = eval(value.replace('\\', ''))[0]
                post_lable['platetype'] = eval(value.replace('\\', ''))[0]
            else:
                post_lable[key] = round(eval(value)[1] - eval(value)[0], 4)
        SQLQueryFront ='''
        select
        dd.upid,
        dd.platetype,
        dd.tgtwidth,
        dd.tgtlength,
        dd.tgtthickness,
        dd.toc,
        dd.fqc_label as label,
        dd.status_fqc,
        lmp.thicknessos,
        lmp.thicknessclosetotal
        from  app.deba_dump_data dd 
        left join dcenter.l2_m_plate lmp
        on lmp.upid = dd.upid'''

        SQLquery = SQLQueryFront + '''
        where {tgtthickness}
        and {tgtwidth} 
        and {tgtlength}
        and {platetype}
        order by dd.toc
        limit {limit}
        '''.format(tgtthickness='1=1' if args['tgtthickness'] == '[]' else "dd.tgtthickness >= " + str(eval(args['tgtthickness'])[0]) + " and dd.tgtthickness <= " + str(eval(args['tgtthickness'])[1]),
               tgtwidth='1=1' if args['tgtwidth'] == '[]' else  "dd.tgtwidth >= " + str(eval(args['tgtwidth'])[0]) + " and dd.tgtwidth <= " + str(eval(args['tgtwidth'])[1]),
               tgtlength='1=1' if args['tgtlength'] == '[]' else "dd.tgtlength >= " + str(eval(args['tgtlength'])[0]) + " and dd.tgtlength <= " + str(eval(args['tgtlength'])[1]),
               platetype = "dd.platetype = '" + str(eval(args['platetype'].replace('\\', ''))[0]) + "' ",
               limit= int(limit)
                )
        configArr = readConfig()
        conn = psycopg2.connect(database=configArr[0], user=configArr[1], password=configArr[2], host=configArr[3],
                                port=configArr[4])
        cursor = conn.cursor()
        cursor.execute(SQLquery)
        rows = cursor.fetchall()

        # Extract the column names
        col_names = []
        for elt in cursor.description:
            col_names.append(elt[0])

        conn.close()
        return post_lable, rows, col_names

    @staticmethod
    def getMareyDataDBTime(time):
        SQLQueryFront = '''
                select
                dd.upid,
                dd.platetype,
                dd.tgtwidth,
                dd.tgtlength,
                dd.tgtthickness,
                dd.toc,
                dd.fqc_label as label,
                dd.status_fqc,
                lmp.thicknessos,
                lmp.thicknessclosetotal
                from  app.deba_dump_data dd 
                left join dcenter.l2_m_plate lmp
                on lmp.upid = dd.upid'''

        SQLquery = SQLQueryFront + '''
        where {toc}
        order by dd.toc
        '''.format(toc ="dd.toc >= '" + str(time['start']) + "' and dd.toc < '" + str(time['end']) + "'"
                )
        configArr = readConfig()
        conn = psycopg2.connect(database=configArr[0], user=configArr[1], password=configArr[2], host=configArr[3],
                                port=configArr[4])
        cursor = conn.cursor()
        cursor.execute(SQLquery)
        rows = cursor.fetchall()

        # Extract the column names
        col_names = []
        for elt in cursor.description:
            col_names.append(elt[0])

        conn.close()
        return rows, col_names
        # parser.add_argument("productcategory", type=str, required=True)
        # parser.add_argument("steelspec", type=str, required=True)
        # parser.add_argument("status_cooling", type=str, required=True)
        # parser.add_argument("fqcflag", type=str, required=True)

