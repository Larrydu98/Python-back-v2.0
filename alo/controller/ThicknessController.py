import numpy as np
import pandas as pd
import json
import datetime as dt
import time

from ..DBCMoudles.getThicknessDataDB import *


class ComputeThicknessData:
    def __init__(self, parser, plate_limit, day_limit, hour_limit):
        self.parase_test = parser
        self.day_variable = int(day_limit)
        self.hour_variable = int(hour_limit)
        self.post_lable, rows, col_names = getThicknessDataDB.getMareyDataDB(parser, plate_limit)
        self.test_data = pd.DataFrame(data=rows, columns=col_names).dropna(axis=0, how='all').reset_index(drop=True)
        self.test_data.index = self.test_data.toc
        self.upid_list = list(self.test_data.upid)

    @property
    def printData(self):
        '''
        day_variable 天数的密度
        hour_variable 小时的密度
        select_time 是最终此段的连续时间和不连续的前后三个小时的
        '''
        print(self.parase_test)
        three_hour = dt.timedelta(hours=3)
        day_list = self.timeDensity(self.test_data, self.day_variable, 'D')
        # 时间的列表数组
        select_time = []
        for index, val in enumerate(day_list):
            middle_data = self.timeDensity(val, self.hour_variable, 'H')
            if len(middle_data) > 5:
                select_time.append({
                    "start": (middle_data[0]['toc'][0]).strftime("%Y-%m-%d %H:%M:%S"),
                    "end": (
                        middle_data[len(middle_data) - 1]['toc'][len(middle_data[len(middle_data) - 1]) - 1]).strftime(
                        "%Y-%m-%d %H:%M:%S"),
                })
            if (len(middle_data) > 0) & (len(middle_data) <= 5):
                select_time.append({
                    "start": (middle_data[0]['toc'][0] - three_hour).strftime("%Y-%m-%d %H:%M:%S"),
                    "end": (middle_data[len(middle_data) - 1]['toc'][
                                len(middle_data[len(middle_data) - 1]) - 1] + three_hour).strftime("%Y-%m-%d %H:%M:%S")
                })
        # 遍历获取最终数据final_arr存储的是连续时间的开始时间和结束时间以及不连续的前三个小时和后个小时的数据连续定义
        # 就是上面的middle_data相比的数值。
        final_arr = []
        res = []
        for i in select_time:
            flag = True
            rows, col_names = getThicknessDataDB.getMareyDataDBTime(i)
            df = pd.DataFrame(data=rows, columns=col_names).dropna(axis=0, how='all').reset_index(drop=True)
            # 对选取的数据是否是自己进行编码。是的话就是true否则就是false
            for row_index, row_data in df.iterrows():
                if row_data['upid'] in self.upid_list:
                    df.loc[row_index, 'self_coding'] = 'true'
                else:
                    df.loc[row_index, 'self_coding'] = 'false'

            # s_list就是篮子
            s_list = self.getSpeciFication(df)
            # 对照篮子进行编码并同时过滤数据
            df = self.dataCodingAndFilter(df, s_list)
            # 大于半个小时进行分隔
            df_arr = self.splitData(df, "dataframe")

            for j in df_arr:
                df_cluster = self.dataCluster(j)
            # 判断是又有自己，有自己的话就append。else。不append
            for self_index, self_df in enumerate(df_cluster):
                self_series = self_df['self_coding'].value_counts(normalize=True)
                if self_series[self_series > 0.8].index == 'true':
                    df_cluster.append(self_index)
                    flag = not flag
                    break
            if flag:
                continue

            res_list = []
            for index, val in enumerate(df_cluster):
                # len(val[(val['status_fqc'] == 1) / len(val)
                if index != len(df_cluster) - 1:
                    good_flag = round(len(val[(val['status_fqc'] == 0) & (val['thicknessflag'] == '[1, 1, 1, 1, 1]')]) / len(val), 2)
                    bad_flag = round(len(val[(val['status_fqc'] == 0) & (val['thicknessflag'] != '[1, 1, 1, 1, 1]')]) / len(val), 2)
                    no_flag = round(len(val[val['status_fqc'] == 1]) / len(val), 2)
                    if index == df_cluster[-1]:
                        res_list.append({
                            "startTime": val.iloc[0].toc.strftime("%Y-%m-%d %H:%M:%S"),
                            "endTime": val.iloc[len(val) - 1].toc.strftime("%Y-%m-%d %H:%M:%S"),
                            "platetype": val.iloc[0].platetype,
                            "tgtwidth_avg": round(val.tgtwidth.mean(), 3),
                            "tgtlength_avg": round(val.tgtlength.mean(), 3),
                            "tgtthickness_avg": round(val.tgtthickness.mean(), 5),
                            "tgtwidth_std": round(val.tgtwidth.std(), 5),
                            "tgtlength_std": round(val.tgtlength.std(), 5),
                            "tgtthickness_std": round(val.tgtthickness.std(), 5),
                            "plate_number": len(val),
                            "good_flag": good_flag,
                            "bad_flag": bad_flag,
                            "no_flag": no_flag,
                            "flag_time": (val.iloc[0].toc + (val.iloc[len(val) - 1].toc - val.iloc[0].toc) / 2).strftime("%Y-%m-%d %H:%M:%S"),
                            "match_flag": 1
                        })
                    else:
                        res_list.append({
                            "startTime": val.iloc[0].toc.strftime("%Y-%m-%d %H:%M:%S"),
                            "endTime": val.iloc[len(val) - 1].toc.strftime("%Y-%m-%d %H:%M:%S"),
                            "platetype": val.iloc[0].platetype,
                            "tgtwidth_avg": round(val.tgtwidth.mean(), 3),
                            "tgtlength_avg": round(val.tgtlength.mean(), 3),
                            "tgtthickness_avg": round(val.tgtthickness.mean(), 5),
                            "tgtwidth_std": round(val.tgtwidth.std(), 5),
                            "tgtlength_std": round(val.tgtlength.std(), 5),
                            "tgtthickness_std": round(val.tgtthickness.std(), 5),
                            "plate_number": len(val),
                            "good_flag": good_flag,
                            "bad_flag": bad_flag,
                            "no_flag": no_flag,
                            "flag_time": (val.iloc[0].toc + (val.iloc[len(val) - 1].toc - val.iloc[0].toc) / 2).strftime("%Y-%m-%d %H:%M:%S"),
                            "match_flag": 0
                        })


            for index, val in enumerate(res_list):
                if index == 0:
                    continue
                else:
                    last_index = index - 1
                    last_time = time.mktime(time.strptime(res_list[last_index]['flag_time'], "%Y-%m-%d %H:%M:%S"))
                    now_time = time.mktime(time.strptime(val['flag_time'], "%Y-%m-%d %H:%M:%S"))
                    if now_time - last_time > 0:
                        continue
                    else:
                        del res_list[index]


            res.append(res_list)
            # final_arr.append(df_cluster)
        return res

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
            time_difference = dt.timedelta(days=1)
        else:
            time_difference = dt.timedelta(hours=1)
        for index, value in series.items():
            if (value > density):
                time_arr.append({'time': [str(index), str(index + time_difference)], 'value': value})

        for i in time_arr:
            data_arr.append(data.loc[i['time'][0]:i['time'][1]])
        return data_arr

    def getSpeciFication(self, df):
        '''
        拿到总指标的篮子
        '''
        specification_list = {}
        for key in self.post_lable:
            if (key == "platetype"):
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

    def dataCodingAndFilter(self, df, s_list):
        '''
        进行编码筛选数据
        没有编码到的就是null
        最后删除null的数据
        '''
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
                df.loc[row_index, 'coding'] = ''.join(str(i) for i in coding_list)
            else:
                df.loc[row_index, 'coding'] = 'null'
        df = df[df['coding'] != 'null']
        df = df.reset_index(drop=True)
        # middle_df = df.groupby(df['coding']).count()
        # shift_coding = list(middle_df.drop(middle_df[middle_df.upid < 5].index).index)
        # df = df[df.coding.isin(shift_coding)]
        return df

    def splitData(self, data, type_value):
        '''
        定义分隔数组或者分隔dataframe
        dataframe用toc间隔大于半个小时进行分隔
        数组用两个数字之间的差大于10进行分隔
        '''

        if type_value == 'dataframe':
            interval_df = []
            index_location = 0
            for index, row in data.iterrows():
                if index == 0:
                    continue
                else:
                    if (row['toc'] - data.iloc[index - 1].at['toc']) > dt.timedelta(hours=0.5):
                        if (index - index_location) > 5:
                            interval_df.append(data.iloc[index_location:index, ])
                        index_location = index
            #         print(df.iloc[index].at['toc'])
            if (len(data) - index_location) > 4:
                interval_df.append(data.iloc[index_location:len(data), ])
            return interval_df
        else:
            interval_list = []
            index_location = 0
            for index, value in enumerate(data):
                if index == 0:
                    continue
                else:
                    if (value - data[index - 1]) > 5:
                        interval_list.append(interval_list[index_location: index])
                        index_location = index
            interval_list.append(data[index_location:])
            return interval_list

    def dataCluster(self, data):
        '''传入一个dataframe
        return一个list 包含有聚类结束的所有类别的dataframe
        '''
        middle_df = data.groupby(data['coding']).count()
        standards_list = list(middle_df.drop(middle_df[middle_df.upid < 5].index).index)
        all_list = []
        for i in standards_list:
            coding_list = list(data[data['coding'] == i].index)
            coding_list = self.splitData(coding_list, 'list')
            for j in coding_list:
                if len(j) > 3:
                    all_list.append(data.loc[j])
                else:
                    continue
        all_list = sorted(all_list, key=lambda x: x.iloc[0].toc)
        return all_list
