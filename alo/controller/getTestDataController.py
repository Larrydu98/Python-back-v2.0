import numpy as np
import pandas as pd
import datetime as dt
import json
import datetime, time

from ..DBCMoudles.getTestDataDB import GetTestData

class ComputerTestData:
    def __init__(self, parser, limit):
        self.post_lable, rows, col_names = GetTestData.getMareyDataDB(parser, limit)
        self.test_data = pd.DataFrame(data=rows, columns=col_names).dropna(axis=0, how='all').reset_index(drop=True)
        # print(self.post_lable)

    def printData(self):
        '''
        day_variable 天数的密度
        hour_variable 小时的密度
        select_time 是最终此段的连续时间和不连续的前后三个小时的
        '''
        day_variable = 80
        hour_variable = 15
        three_hour = datetime.timedelta(hours=3)
        self.test_data.index = self.test_data.toc
        day_list = self.timeDensity(self.test_data, day_variable, 'D')
        # 时间的列表数组
        select_time = []
        for index, val in enumerate(day_list):
            middle_data = self.timeDensity(val, hour_variable, 'H')
            if (len( middle_data ) > 5):
                select_time.append({
                    "start": (middle_data[0]['toc'][0]).strftime("%Y-%m-%d %H:%M:%S"),
                    "end": (
                    middle_data[len(middle_data) - 1]['toc'][len(middle_data[len(middle_data) - 1]) - 1]).strftime(
                        "%Y-%m-%d %H:%M:%S"),
                })
            if ((len(middle_data) > 0) & (len(middle_data) <= 5)):
                select_time.append({
                    "start": (middle_data[0]['toc'][0] - three_hour).strftime("%Y-%m-%d %H:%M:%S"),
                    "end": (middle_data[len(middle_data) - 1]['toc'][
                                len(middle_data[len(middle_data) - 1]) - 1] + three_hour).strftime("%Y-%m-%d %H:%M:%S")
                })

        # 遍历获取最终数据final_arr存储的是连续时间的开始时间和结束时间以及不连续的前三个小时和后个小时的数据连续定义
        # 就是上面的middle_data相比的数值。
        final_arr = []
        for i in select_time:
            s_list = {}
            rows, col_names = GetTestData.getMareyDataDBTime(i)
            df = pd.DataFrame(data=rows, columns=col_names).dropna(axis=0, how='all').reset_index(drop=True)
            # s_list就是篮子
            s_list = self.getSpeciFication(df)
            df = self.dataClassification(df, s_list)
            print(df)




            final_arr.append(df)




        return 'test'



    def timeDensity(self, data, density, rule):
        '''
        此是的作用是获取
        data:dataframe
        density：密度就是限定的密度
        rule：resample规则
        '''
        series = data.toc
        series = series.resample(rule).count()
        time_arr = []
        data_arr = []
        if rule == 'D':
            time_difference = datetime.timedelta(days=1)
        else:
            time_difference = datetime.timedelta(hours=1)
        for index, value in series.items():
            if (value > density):
                time_arr.append({'time': [str(index), str(index + time_difference)], 'value': value})

        for i in time_arr:
            data_arr.append(data.loc[i['time'][0]:i['time'][1]])
        return data_arr

    def getSpeciFication(self, df):
        specification_list = {}
        for key in self.post_lable:
            if(key == "platetype"):
                mid_plate = df.groupby(df['platetype']).count()
                s_plate = list(mid_plate.drop(mid_plate[mid_plate.upid < 5].index).index)
                specification_list['platetype'] = s_plate
            else:
                df_max = df.loc[df[key].idxmax()][key]
                df_min = df.loc[df[key].idxmin()][key]
                s_bin = []
                # 指标数组
                s_list = []
                point_move = df_min - self.post_lable[key] / 10
                while point_move <= df_max:
                    s_bin.append(point_move)
                    point_move += self.post_lable[key]
                s_bin.append(point_move)
                for index, value in pd.cut(df[key], bins=s_bin).value_counts().sort_index().items():
                    # 此处的10是自己定义的用于判断同一种类的超过多少是同一类型
                    if (value >= 10):
                        s_list.append(index)
                specification_list[key] = s_list
        return specification_list

    def dataClassification(self, df, s_list):
        for row_index, row in df.iterrows():
            coding_list = []
            for key in s_list:
                if key == 'platetype':
                    if row['platetype'] in s_list['platetype']:
                        coding_list.append(s_list['platetype'].index(row['platetype']))
                else:
                    value = s_list[key]
                    for index, item in enumerate(value):
                        if row[key] in item:
                            coding_list.append(index)
                            break
            if len(coding_list) == 4:
                df.loc[row_index, 'coding'] = ''.join(str(yaya) for yaya in coding_list)
            else:
                df.loc[row_index, 'coding'] = 'null'
        df = df[df['coding'] != 'null']
        return df










