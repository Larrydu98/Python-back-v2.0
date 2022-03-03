import numpy as np
import pandas as pd
import datetime as dt
import time

from ..models.getMareyDataFromDB import *


class newComputeMareyData:
    def __init__(self, type, upid, start_time, end_time, steelspec, tgtplatethickness):

        rows, col_names = GetMareyData.getMareyData(type, upid, start_time, end_time, steelspec, tgtplatethickness)
        flag, _ = GetMareyData.getMareyFlag(upid, start_time, end_time)

        self.flag = {}
        for item in flag:
            label = 0
            if item[2] == 0:
                flags = item[1]['method1']['data']
                if np.array(flags).sum() == 5:
                    label = 1
            elif item[2] == 1:
                label = 404
            self.flag[item[0]] = label

        self.marey_data = pd.DataFrame(data=rows, columns=col_names).dropna(axis=0, how='all').reset_index(drop=True)
        # self.marey_data.cooling_start_temp = self.marey_data.cooling_start_temp.replace('None',0)
        # self.marey_data.cooling_stop_temp = self.marey_data.cooling_stop_temp.replace('None',0)
        # self.marey_data.cooling_rate1 = self.marey_data.cooling_rate1.replace('None',0)
        if(type=="stations"):
            index = pd.MultiIndex.from_arrays([self.marey_data.upid.values.tolist()], names=['upid'])
        else:
            index = pd.MultiIndex.from_arrays([self.marey_data.upid.values.tolist(), self.marey_data.pass_no.values.tolist()], names=['upid', 'pass_no'])
        self.marey_data.index = index

        # print(len(self.marey_data))

    def printData(self):
        print(self.marey_data)

    def newGetMareyStations(self):
        if len(self.marey_data) == 0:
            return 204, []

        mareystations = []
        fu_name = ['FuCharging', 'FuPre', 'FuHeating1', 'FuHeating2', 'FuSoak', 'FuDischarging']
        rm_name = ['RmStart', 'RmF3Pass', 'RmL3Pass', 'RmEnd']
        fm_name = ['FmStart', 'FmF3Pass', 'FmL3Pass', 'FmEnd']
        cc_name = ['CcStart', 'CcDQEnd', 'CcACCEnd']
        cc_flag = int(self.marey_data.adcontrolcode.max())

        for i in range(len(fu_name)):
            mareystations.append({'key': '010' + str(i + 1),
                                  'name': fu_name[i],
                                  'distance': i * 40,
                                  'zone': '1'})

        for i in range(len(rm_name)):
            mareystations.append({'key': '020' + str(i + 1),
                                  'name': rm_name[i],
                                  'distance': (len(fu_name) + i) * 40,
                                  'zone': '2'})

        for i in range(len(fm_name)):
            mareystations.append({'key': '030' + str(i + 1),
                                  'name': fm_name[i],
                                  'distance': (len(fu_name) + len(rm_name) + i) * 40,
                                  'zone': '3'})
        if cc_flag > 0:
            for i in range(len(cc_name)):
                mareystations.append({'key': '040' + str(i + 1),
                                      'name': cc_name[i],
                                      'distance': (len(fu_name) + len(rm_name) + len(fm_name) + i) * 40,
                                      'zone': '4'})

        return 200, mareystations


    def newGetMareyTimes(self, compressed_factor):

        if len(self.marey_data) == 0:
            return 204, []

        mareydata = []
        upids = self.marey_data.upid.unique()
        # print(upids)

        for i in range(len(upids)):
            # print(upids[i])
            # if upids[i] == '20708267000':
            #     print('get')

            # 参数初始化
            stops = []
            ## 压缩系数
            compressed_factor = int(compressed_factor)
            plate_data = self.marey_data.loc[upids[i]].loc[1]
            ## 去除重复道次数据
            if plate_data.shape != (31,):
                plate_data = self.marey_data.loc[upids[i]].loc[1].iloc[0, ]
            if np.isnan(plate_data.totalpassesrm) or np.isnan(plate_data.totalpassesfm):
                continue
            rm_pass = int(plate_data.totalpassesrm)
            fm_pass = int(plate_data.totalpassesfm)
            m_total_pass = rm_pass + fm_pass
            m_pass_series = self.marey_data[self.marey_data.upid == upids[i]].pass_no
            rm_pass_ndarray = np.unique(m_pass_series[m_pass_series <= rm_pass].values)
            fm_pass_ndarray = np.unique(m_pass_series[m_pass_series > rm_pass].values)
            m_total_pass = len(rm_pass_ndarray) + len(fm_pass_ndarray)
            # rm_pass_max = self.marey_data.totalpassesrm.max()
            # fm_pass_max = self.marey_data.totalpassesfm.max()

            fu_name = ['FuCharge', 'FuPre', 'FuHeat1', 'FuHeat2', 'FuSoak', 'FuDischarge']
            rm_name = ['RmStart', 'RmF3Pass', 'RmL3Pass', 'RmEnd']
            fm_name = ['FmStart', 'FmF3Pass', 'FmL3Pass', 'FmEnd']
            cc_name = ['CcStart', 'CcDQEnd', 'CcACCEnd']

            dq_count = self.marey_data[self.marey_data.upid == upids[i]].dq_count

            try:
                flag = self.flag[upids[i]]
            except:
                flag = 404

            # 加热工序站点时间计算
            ## realTime
            fu_discharge_time = plate_data.discharge_time
            fu_charging_time = plate_data.discharge_time - dt.timedelta(minutes=plate_data.in_fce_time)
            staying_time_pre = fu_charging_time + dt.timedelta(minutes=plate_data.staying_time_pre)
            staying_time_1 = staying_time_pre + dt.timedelta(minutes=plate_data.staying_time_1)
            staying_time_2 = staying_time_1 + dt.timedelta(minutes=plate_data.staying_time_2)
            staying_time_soak = staying_time_2 + dt.timedelta(minutes=plate_data.staying_time_soak)
            ## time
            c_fu_discharge_time = fu_discharge_time
            c_staying_time_pre = c_fu_discharge_time - (fu_discharge_time - staying_time_pre) / compressed_factor
            c_staying_time_1 = c_fu_discharge_time - (fu_discharge_time - staying_time_1) / compressed_factor
            c_staying_time_2 = c_fu_discharge_time - (fu_discharge_time - staying_time_2) / compressed_factor
            c_staying_time_soak = c_fu_discharge_time - (fu_discharge_time - staying_time_soak) / compressed_factor
            c_fu_charging_time = c_fu_discharge_time - (fu_discharge_time - fu_charging_time) / compressed_factor
            fuTotalTimeAfter = (c_fu_discharge_time - c_fu_charging_time).total_seconds()

            ## 数据储存
            stops.append({'station': {'key': '0101', 'name': fu_name[0], 'distance': 0.0, 'zone': '1'}, 'realTime': str(fu_charging_time),
                          'time': str(c_fu_charging_time)[0:19]})
            stops.append({'station': {'key': '0102', 'name': fu_name[1], 'distance': 40.0, 'zone': '1'}, 'realTime': str(staying_time_pre),
                          'time': str(c_staying_time_pre)[0:19]})
            stops.append({'station': {'key': '0103', 'name': fu_name[2], 'distance': 80.0, 'zone': '1'}, 'realTime': str(staying_time_1),
                          'time': str(c_staying_time_1)[0:19]})
            stops.append({'station': {'key': '0104', 'name': fu_name[3], 'distance': 120.0, 'zone': '1'}, 'realTime': str(staying_time_2),
                          'time': str(c_staying_time_2)[0:19]})
            stops.append({'station': {'key': '0105', 'name': fu_name[4], 'distance': 160.0, 'zone': '1'}, 'realTime': str(staying_time_soak),
                          'time': str(c_staying_time_soak)[0:19]})
            stops.append({'station': {'key': '0106', 'name': fu_name[5], 'distance': 200.0, 'zone': '1'}, 'realTime': str(fu_discharge_time),
                          'time': str(c_fu_discharge_time)[0:19]})

            rolling_data = self.marey_data.loc[upids[i]]
            mtotalTime = (dt.datetime.strptime(rolling_data.iloc[-1,].starttime[0:14], "%Y%m%d%H%M%S") - \
                         dt.datetime.strptime(rolling_data.iloc[0,].starttime[0:14], "%Y%m%d%H%M%S")).total_seconds()
            # 粗轧工序站点时间计算
            if rm_pass != 0:
                if rm_pass <= 3:
                    rmstart_time = dt.datetime.strptime(rolling_data.iloc[0,].starttime[0:14], "%Y%m%d%H%M%S")
                    stops.append({'station': {'key': '0201', 'name': rm_name[0], 'distance': 240.0, 'zone': '2'}, 'realTime': str(rmstart_time),
                                  'time': str(rmstart_time)})
                    rmf3pass_time = dt.datetime.strptime(rolling_data.iloc[rm_pass - 1,].finishtime[0:14], "%Y%m%d%H%M%S")
                    rmf3zp = rolling_data.iloc[0:3, ].zeropoint.apply(lambda x: round(x, 5)).values.tolist()
                    stops.append({'station': {'key': '0202', 'name': rm_name[1], 'distance': 280.0, 'zone': '2', 'zeropoint': rmf3zp}, 'realTime': str(rmf3pass_time),
                                  'time': str(rmf3pass_time)})
                elif rm_pass > 3 and rm_pass <= 6:
                    rmstart_time = dt.datetime.strptime(rolling_data.iloc[0,].starttime[0:14], "%Y%m%d%H%M%S")
                    stops.append({'station': {'key': '0201', 'name': rm_name[0], 'distance': 240.0, 'zone': '2'}, 'realTime': str(rmstart_time),
                                  'time': str(rmstart_time)})
                    rmf3pass_time = dt.datetime.strptime(rolling_data.iloc[2,].finishtime[0:14], "%Y%m%d%H%M%S")
                    rmf3zp = rolling_data.iloc[0:3, ].zeropoint.apply(lambda x: round(x, 5)).values.tolist()
                    stops.append({'station': {'key': '0202', 'name': rm_name[1], 'distance': 280.0, 'zone': '2', 'zeropoint': rmf3zp}, 'realTime': str(rmf3pass_time),
                                  'time': str(rmf3pass_time)})
                    rml3pass_time = dt.datetime.strptime(rolling_data.iloc[rm_pass - 1,].starttime[0:14], "%Y%m%d%H%M%S")
                    stops.append({'station': {'key': '0203', 'name': rm_name[2], 'distance': 320.0, 'zone': '2'}, 'realTime': str(rml3pass_time),
                                  'time': str(rml3pass_time)})
                elif rm_pass > 6:
                    rmstart_time = dt.datetime.strptime(rolling_data.iloc[0,].starttime[0:14], "%Y%m%d%H%M%S")
                    stops.append({'station': {'key': '0201', 'name': rm_name[0], 'distance': 240.0, 'zone': '2'}, 'realTime': str(rmstart_time),
                                  'time': str(rmstart_time)})
                    rmf3pass_time = dt.datetime.strptime(rolling_data.iloc[2,].finishtime[0:14], "%Y%m%d%H%M%S")
                    rmf3zp = rolling_data.iloc[0:3, ].zeropoint.apply(lambda x: round(x, 5)).values.tolist()
                    stops.append({'station': {'key': '0202', 'name': rm_name[1], 'distance': 280.0, 'zone': '2', 'zeropoint': rmf3zp}, 'realTime': str(rmf3pass_time),
                                  'time': str(rmf3pass_time)})
                    rml3pass_time = dt.datetime.strptime(rolling_data.iloc[rm_pass - 3,].starttime[0:14], "%Y%m%d%H%M%S")
                    stops.append({'station': {'key': '0203', 'name': rm_name[2], 'distance': 320.0, 'zone': '2'}, 'realTime': str(rml3pass_time),
                                  'time': str(rml3pass_time)})
                    rmend_time = dt.datetime.strptime(rolling_data.iloc[rm_pass - 1,].finishtime[0:14], "%Y%m%d%H%M%S")
                    stops.append({'station': {'key': '0204', 'name': rm_name[3], 'distance': 360.0, 'zone': '2'}, 'realTime': str(rmend_time),
                                  'time': str(rmend_time)})

            # 精轧工序站点时间计算
            if fm_pass != 0:
                if fm_pass <= 3:
                    fmstart_time  = dt.datetime.strptime(rolling_data.iloc[rm_pass,].starttime[0:14], "%Y%m%d%H%M%S")
                    stops.append({'station': {'key': '0301', 'name': fm_name[0], 'distance': 400.0, 'zone': '3'}, 'realTime': str(fmstart_time),
                                  'time': str(fmstart_time)})
                    fmf3pass_time = dt.datetime.strptime(rolling_data.iloc[m_total_pass-1,].starttime[0:14], "%Y%m%d%H%M%S")
                    stops.append({'station': {'key': '0302', 'name': fm_name[1], 'distance': 440.0, 'zone': '3'}, 'realTime': str(fmf3pass_time),
                                  'time': str(fmf3pass_time)})
                elif fm_pass > 3 and fm_pass <= 6:
                    fmstart_time = dt.datetime.strptime(rolling_data.iloc[rm_pass,].starttime[0:14], "%Y%m%d%H%M%S")
                    stops.append({'station': {'key': '0301', 'name': fm_name[0], 'distance': 400.0, 'zone': '3'}, 'realTime': str(fmstart_time),
                                  'time': str(fmstart_time)})
                    fmf3pass_time = dt.datetime.strptime(rolling_data.iloc[rm_pass+2,].finishtime[0:14], "%Y%m%d%H%M%S")
                    stops.append({'station': {'key': '0302', 'name': fm_name[1], 'distance': 440.0, 'zone': '3'}, 'realTime': str(fmf3pass_time),
                                  'time': str(fmf3pass_time)})
                    fml3pass_time = dt.datetime.strptime(rolling_data.iloc[m_total_pass - 1,].starttime[0:14], "%Y%m%d%H%M%S")
                    fml3zp = rolling_data.iloc[m_total_pass-3:m_total_pass, ].zeropoint.apply(lambda x: round(x, 5)).values.tolist()
                    stops.append({'station': {'key': '0303', 'name': fm_name[2], 'distance': 480.0, 'zone': '3', 'zeropoint': fml3zp}, 'realTime': str(fml3pass_time),
                                  'time': str(fml3pass_time)})
                elif fm_pass > 6:
                    fmstart_time = dt.datetime.strptime(rolling_data.iloc[rm_pass,].starttime[0:14], "%Y%m%d%H%M%S")
                    stops.append({'station': {'key': '0301', 'name': fm_name[0], 'distance': 400.0, 'zone': '3'}, 'realTime': str(fmstart_time),
                                  'time': str(fmstart_time)})
                    fmf3pass_time = dt.datetime.strptime(rolling_data.iloc[rm_pass + 2,].finishtime[0:14], "%Y%m%d%H%M%S")
                    stops.append({'station': {'key': '0302', 'name': fm_name[1], 'distance': 440.0, 'zone': '3'}, 'realTime': str(fmf3pass_time),
                                  'time': str(fmf3pass_time)})
                    fml3pass_time = dt.datetime.strptime(rolling_data.iloc[m_total_pass-3,].starttime[0:14], "%Y%m%d%H%M%S")
                    fml3zp = rolling_data.iloc[m_total_pass-3:m_total_pass, ].zeropoint.apply(lambda x: round(x, 5)).values.tolist()
                    stops.append({'station': {'key': '0303', 'name': fm_name[2], 'distance': 480.0, 'zone': '3', 'zeropoint': fml3zp}, 'realTime': str(fml3pass_time),
                                  'time': str(fml3pass_time)})
                    fmend_time    = dt.datetime.strptime(rolling_data.iloc[m_total_pass-1,].finishtime[0:14], "%Y%m%d%H%M%S")
                    stops.append({'station': {'key': '0304', 'name': fm_name[3], 'distance': 520.0, 'zone': '3'}, 'realTime': str(fmend_time),
                                  'time': str(fmend_time)})




            # for j in range(len(rm_pass_ndarray)):
            #     rm_data = self.marey_data.loc[upids[i]].loc[rm_pass_ndarray[j]]
            #     ## 去除重复道次数据
            #     if rm_data.shape != (31,):
            #         rm_data = self.marey_data.loc[upids[i]].loc[rm_pass_ndarray[j]].iloc[0,]
            #     rm_time = dt.datetime.strptime(rm_data.starttime[0:14], "%Y%m%d%H%M%S")
            #     ## 数据储存
            #     stops.append({'station': {'key': '020' + str(i + 1),
            #                               'name': rm_name[i],
            #                               'distance': (len(fu_name) + i) * 40,
            #                               'zone': '2'},
            #                   'realTime': str(rm_time),
            #                   'time': str(rm_time)})

            # 精轧工序站点时间计算
            # for j in range(len(fm_pass_ndarray)):
            #     fm_data = self.marey_data.loc[upids[i]].loc[fm_pass_ndarray[j]]
            #     ## 去除重复道次数据
            #     if fm_data.shape != (31,):
            #         fm_data = self.marey_data.loc[upids[i]].loc[fm_pass_ndarray[j]].iloc[0,]
            #     fm_time = dt.datetime.strptime(fm_data.starttime[0:14], "%Y%m%d%H%M%S")
            #     ## 数据储存
            #     stops.append({'station': {'key': '030' + str(i + 1),
            #                               # 'name': str(fm_pass_ndarray[i]),
            #                               'distance': (len(fu_name) + len(rm_name) + i) * 40,
            #                               'zone': '3'},
            #                   'realTime': str(fm_time),
            #                   'time': str(fm_time)})

            # 冷却工序站点时间计算
            if int(plate_data.adcontrolcode) <= 0:
                ccTotalTime = 0.0
                mareydata.append({'upid': plate_data.upid,
                                  'slabid': plate_data.slabid,
                                  'toc': str(plate_data.toc),
                                  'flag': flag,
                                  'steelspec': plate_data.steelspec,
                                  'productcategory': plate_data.productcategory,

                                  'tgtdischargetemp': plate_data.tgtdischargetemp,
                                  'slabthickness': plate_data.slabthickness,
                                  'tgtplatethickness': plate_data.tgtplatethickness,
                                  'tgtwidth': plate_data.tgtwidth,
                                  'tgtplatelength2': plate_data.tgtplatelength2,
                                  'tgttmplatetemp': plate_data.tgttmplatetemp,
                                  'adcontrolcode': plate_data.adcontrolcode,
                                  # 'cooling_start_temp': plate_data.cooling_start_temp,
                                  # 'cooling_stop_temp': plate_data.cooling_stop_temp,
                                  # 'cooling_rate1': plate_data.cooling_rate1,

                                  'stops': stops,
                                  'fuTotalTimeAfter': fuTotalTimeAfter,
                                  'mtotalTime': mtotalTime,
                                  'ccTotalTime': ccTotalTime
                                  })

            else:
                ## cc_start和cc_end时间计算

                if pd.isnull(plate_data.avg_time_b):
                    plate_data.avg_time_b = 0
                if pd.isnull(plate_data.avg_time_w):
                    plate_data.avg_time_w = 0
                cooling_start_time = dt.datetime.strptime(plate_data.timerollingfinish[0:14], "%Y%m%d%H%M%S")
                cc_start = cooling_start_time + dt.timedelta(seconds=plate_data.avg_time_b)
                cc_end = cc_start + dt.timedelta(seconds=plate_data.avg_time_w)

                ## dq_end时间计算
                dq_ratio = plate_data.dq_count / (plate_data.dq_count + plate_data.acc_count)
                if pd.isnull(dq_ratio):
                    dq_ratio = 0
                dq_end = cc_start + (cc_end - cc_start) * dq_ratio
                # cc_start = str(cc_start)[0:19]
                # cc_end = str(cc_end)[0:19]
                ccTotalTime = (cc_end - cc_start).total_seconds()

                ## 数据储存
                stops.append({'station': {'key': '0401',
                                          'name': cc_name[0],
                                          'distance': 560.0,
                                          'zone': '4'},
                              'realTime': str(cc_start)[0:19],
                              'time': str(cc_start)[0:19]})
                stops.append({'station': {'key': '0402',
                                          'name': cc_name[1],
                                          'distance': 600.0,
                                          'zone': '4'},
                              'realTime': str(dq_end)[0:19],
                              'time': str(dq_end)[0:19]})
                stops.append({'station': {'key': '0402',
                                          'name': cc_name[2],
                                          'distance': 640.0,
                                          'zone': '4'},
                              'realTime': str(cc_end)[0:19],
                              'time': str(cc_end)[0:19]})

                if pd.isnull(plate_data.cooling_start_temp) or pd.isnull(plate_data.cooling_stop_temp) or pd.isnull(plate_data.cooling_rate1):
                    plate_data.cooling_start_temp = 0
                    plate_data.cooling_stop_temp = 0
                    plate_data.cooling_rate1 = 0
                # 规格数据、全流程站点数据汇总
                mareydata.append({'upid': plate_data.upid,
                                  'slabid': plate_data.slabid,
                                  'toc': str(plate_data.toc),
                                  'flag': flag,
                                  'steelspec': plate_data.steelspec,
                                  'productcategory': plate_data.productcategory,

                                  'tgtdischargetemp': plate_data.tgtdischargetemp,
                                  'slabthickness': plate_data.slabthickness,
                                  'tgtplatethickness': plate_data.tgtplatethickness,
                                  'tgtwidth': plate_data.tgtwidth,
                                  'tgtplatelength2': plate_data.tgtplatelength2,
                                  'tgttmplatetemp': plate_data.tgttmplatetemp,
                                  'adcontrolcode': plate_data.adcontrolcode,
                                  'cooling_start_temp': plate_data.cooling_start_temp,
                                  'cooling_stop_temp': plate_data.cooling_stop_temp,
                                  'cooling_rate1': plate_data.cooling_rate1,

                                  'stops': stops,
                                  'fuTotalTimeAfter': fuTotalTimeAfter,
                                  'mtotalTime': mtotalTime,
                                  'ccTotalTime': ccTotalTime
                                  })

        if len(mareydata) < 5:
            return 202, mareydata
        return 200, mareydata


class getMareyDataByDumpData:
    def __init__(self, type, upid, start_time, end_time, steelspec, tgtplatethickness):

        rows, col_names = GetMareyData.getMareyData(type, upid, start_time, end_time, steelspec, tgtplatethickness)

        self.marey_data = pd.DataFrame(data=rows, columns=col_names).dropna(axis=0, how='all').reset_index(drop=True)
        # self.marey_data.cooling_start_temp = self.marey_data.cooling_start_temp.replace('None',0)
        # self.marey_data.cooling_stop_temp = self.marey_data.cooling_stop_temp.replace('None',0)
        # self.marey_data.cooling_rate1 = self.marey_data.cooling_rate1.replace('None',0)
        if(type=="stations"):
            index = pd.MultiIndex.from_arrays([self.marey_data.upid.values.tolist()], names=['upid'])
        else:
            index = pd.MultiIndex.from_arrays([self.marey_data.upid.values.tolist(), self.marey_data.pass_no.values.tolist()], names=['upid', 'pass_no'])
        self.marey_data.index = index

    def newGetMareyTimes(self, compressed_factor):

        if len(self.marey_data) == 0:
            return 204, []

        mareydata = []
        upids = self.marey_data.upid.unique()
        # print(upids)

        for i in range(len(upids)):
            # print(upids[i])
            # 参数初始化
            stops = []
            ## 压缩系数
            compressed_factor = int(compressed_factor)
            plate_data = self.marey_data.loc[upids[i]].loc[1]
            ## 去除重复道次数据
            if plate_data.shape != (31,):
                plate_data = self.marey_data.loc[upids[i]].loc[1].iloc[0,]
            rm_pass = plate_data.totalpassesrm
            fm_pass = plate_data.totalpassesfm
            m_total_pass = rm_pass + fm_pass
            m_pass_series = self.marey_data[self.marey_data.upid == upids[i]].pass_no
            rm_pass_ndarray = np.unique(m_pass_series[m_pass_series <= rm_pass].values)
            fm_pass_ndarray = np.unique(m_pass_series[m_pass_series > rm_pass].values)
            m_total_pass = len(rm_pass_ndarray) + len(fm_pass_ndarray)
            # rm_pass_max = self.marey_data.totalpassesrm.max()
            # fm_pass_max = self.marey_data.totalpassesfm.max()

            fu_name = ['FuCharge', 'FuPre', 'FuHeat1', 'FuHeat2', 'FuSoak', 'FuDischarge']
            rm_name = ['RmStart', 'RmF3Pass', 'RmL3Pass', 'RmEnd']
            fm_name = ['FmStart', 'FmF3Pass', 'FmL3Pass', 'FmEnd']
            cc_name = ['CcStart', 'CcDQEnd', 'CcACCEnd']

            # 加热工序站点时间计算
            ## realTime
            fu_discharge_time = plate_data.discharge_time
            fu_charging_time = plate_data.discharge_time - dt.timedelta(minutes=plate_data.in_fce_time)
            staying_time_pre = fu_charging_time + dt.timedelta(minutes=plate_data.staying_time_pre)
            staying_time_1 = staying_time_pre + dt.timedelta(minutes=plate_data.staying_time_1)
            staying_time_2 = staying_time_1 + dt.timedelta(minutes=plate_data.staying_time_2)
            staying_time_soak = staying_time_2 + dt.timedelta(minutes=plate_data.staying_time_soak)
            ## time
            c_fu_discharge_time = fu_discharge_time
            c_staying_time_pre = c_fu_discharge_time - (fu_discharge_time - staying_time_pre) / compressed_factor
            c_staying_time_1 = c_fu_discharge_time - (fu_discharge_time - staying_time_1) / compressed_factor
            c_staying_time_2 = c_fu_discharge_time - (fu_discharge_time - staying_time_2) / compressed_factor
            c_staying_time_soak = c_fu_discharge_time - (fu_discharge_time - staying_time_soak) / compressed_factor
            c_fu_charging_time = c_fu_discharge_time - (fu_discharge_time - fu_charging_time) / compressed_factor
            fuTotalTimeAfter = (c_fu_discharge_time - c_fu_charging_time).total_seconds()

            ## 数据储存
            stops.append({'station': {'key': '0101', 'name': fu_name[0], 'distance': 0.0, 'zone': '1'}, 'realTime': str(fu_charging_time),
                          'time': str(c_fu_charging_time)[0:19]})
            stops.append({'station': {'key': '0102', 'name': fu_name[1], 'distance': 40.0, 'zone': '1'}, 'realTime': str(staying_time_pre),
                          'time': str(c_staying_time_pre)[0:19]})
            stops.append({'station': {'key': '0103', 'name': fu_name[2], 'distance': 80.0, 'zone': '1'}, 'realTime': str(staying_time_1),
                          'time': str(c_staying_time_1)[0:19]})
            stops.append({'station': {'key': '0104', 'name': fu_name[3], 'distance': 120.0, 'zone': '1'}, 'realTime': str(staying_time_2),
                          'time': str(c_staying_time_2)[0:19]})
            stops.append({'station': {'key': '0105', 'name': fu_name[4], 'distance': 160.0, 'zone': '1'}, 'realTime': str(staying_time_soak),
                          'time': str(c_staying_time_soak)[0:19]})
            stops.append({'station': {'key': '0106', 'name': fu_name[5], 'distance': 200.0, 'zone': '1'}, 'realTime': str(fu_discharge_time),
                          'time': str(c_fu_discharge_time)[0:19]})

            rolling_data = self.marey_data.loc[upids[i]]
            mtotalTime = (dt.datetime.strptime(rolling_data.iloc[-1,].starttime[0:14], "%Y%m%d%H%M%S") - \
                         dt.datetime.strptime(rolling_data.iloc[0,].starttime[0:14], "%Y%m%d%H%M%S")).total_seconds()
            # 粗轧工序站点时间计算
            if rm_pass != 0:
                if rm_pass <= 3:
                    rmstart_time = dt.datetime.strptime(rolling_data.iloc[0,].starttime[0:14], "%Y%m%d%H%M%S")
                    stops.append({'station': {'key': '0201', 'name': rm_name[0], 'distance': 240.0, 'zone': '2'}, 'realTime': str(rmstart_time),
                                  'time': str(rmstart_time)})
                    rmf3pass_time = dt.datetime.strptime(rolling_data.iloc[rm_pass - 1,].finishtime[0:14], "%Y%m%d%H%M%S")
                    stops.append({'station': {'key': '0202', 'name': rm_name[1], 'distance': 280.0, 'zone': '2'}, 'realTime': str(rmf3pass_time),
                                  'time': str(rmf3pass_time)})
                elif rm_pass > 3 and rm_pass <= 6:
                    rmstart_time = dt.datetime.strptime(rolling_data.iloc[0,].starttime[0:14], "%Y%m%d%H%M%S")
                    stops.append({'station': {'key': '0201', 'name': rm_name[0], 'distance': 240.0, 'zone': '2'}, 'realTime': str(rmstart_time),
                                  'time': str(rmstart_time)})
                    rmf3pass_time = dt.datetime.strptime(rolling_data.iloc[2,].finishtime[0:14], "%Y%m%d%H%M%S")
                    stops.append({'station': {'key': '0202', 'name': rm_name[1], 'distance': 280.0, 'zone': '2'}, 'realTime': str(rmf3pass_time),
                                  'time': str(rmf3pass_time)})
                    rml3pass_time = dt.datetime.strptime(rolling_data.iloc[rm_pass - 1,].starttime[0:14], "%Y%m%d%H%M%S")
                    stops.append({'station': {'key': '0203', 'name': rm_name[2], 'distance': 320.0, 'zone': '2'}, 'realTime': str(rml3pass_time),
                                  'time': str(rml3pass_time)})
                elif rm_pass > 6:
                    rmstart_time = dt.datetime.strptime(rolling_data.iloc[0,].starttime[0:14], "%Y%m%d%H%M%S")
                    stops.append({'station': {'key': '0201', 'name': rm_name[0], 'distance': 240.0, 'zone': '2'}, 'realTime': str(rmstart_time),
                                  'time': str(rmstart_time)})
                    rmf3pass_time = dt.datetime.strptime(rolling_data.iloc[2,].finishtime[0:14], "%Y%m%d%H%M%S")
                    stops.append({'station': {'key': '0202', 'name': rm_name[1], 'distance': 280.0, 'zone': '2'}, 'realTime': str(rmf3pass_time),
                                  'time': str(rmf3pass_time)})
                    rml3pass_time = dt.datetime.strptime(rolling_data.iloc[rm_pass - 3,].starttime[0:14], "%Y%m%d%H%M%S")
                    stops.append({'station': {'key': '0203', 'name': rm_name[2], 'distance': 320.0, 'zone': '2'}, 'realTime': str(rml3pass_time),
                                  'time': str(rml3pass_time)})
                    rmend_time = dt.datetime.strptime(rolling_data.iloc[rm_pass - 1,].finishtime[0:14], "%Y%m%d%H%M%S")
                    stops.append({'station': {'key': '0204', 'name': rm_name[3], 'distance': 360.0, 'zone': '2'}, 'realTime': str(rmend_time),
                                  'time': str(rmend_time)})

            # 精轧工序站点时间计算
            if fm_pass != 0:
                if fm_pass <= 3:
                    fmstart_time  = dt.datetime.strptime(rolling_data.iloc[rm_pass,].starttime[0:14], "%Y%m%d%H%M%S")
                    stops.append({'station': {'key': '0301', 'name': fm_name[0], 'distance': 400.0, 'zone': '3'}, 'realTime': str(fmstart_time),
                                  'time': str(fmstart_time)})
                    fmf3pass_time = dt.datetime.strptime(rolling_data.iloc[m_total_pass-1,].starttime[0:14], "%Y%m%d%H%M%S")
                    stops.append({'station': {'key': '0302', 'name': fm_name[1], 'distance': 440.0, 'zone': '3'}, 'realTime': str(fmf3pass_time),
                                  'time': str(fmf3pass_time)})
                elif fm_pass > 3 and fm_pass <= 6:
                    fmstart_time = dt.datetime.strptime(rolling_data.iloc[rm_pass,].starttime[0:14], "%Y%m%d%H%M%S")
                    stops.append({'station': {'key': '0301', 'name': fm_name[0], 'distance': 400.0, 'zone': '3'}, 'realTime': str(fmstart_time),
                                  'time': str(fmstart_time)})
                    fmf3pass_time = dt.datetime.strptime(rolling_data.iloc[rm_pass+2,].finishtime[0:14], "%Y%m%d%H%M%S")
                    stops.append({'station': {'key': '0302', 'name': fm_name[1], 'distance': 440.0, 'zone': '3'}, 'realTime': str(fmf3pass_time),
                                  'time': str(fmf3pass_time)})
                    fml3pass_time = dt.datetime.strptime(rolling_data.iloc[m_total_pass - 1,].starttime[0:14], "%Y%m%d%H%M%S")
                    stops.append({'station': {'key': '0303', 'name': fm_name[2], 'distance': 480.0, 'zone': '3'}, 'realTime': str(fml3pass_time),
                                  'time': str(fml3pass_time)})
                elif fm_pass > 6:
                    fmstart_time = dt.datetime.strptime(rolling_data.iloc[rm_pass,].starttime[0:14], "%Y%m%d%H%M%S")
                    stops.append({'station': {'key': '0301', 'name': fm_name[0], 'distance': 400.0, 'zone': '3'}, 'realTime': str(fmstart_time),
                                  'time': str(fmstart_time)})
                    fmf3pass_time = dt.datetime.strptime(rolling_data.iloc[rm_pass + 2,].finishtime[0:14], "%Y%m%d%H%M%S")
                    stops.append({'station': {'key': '0302', 'name': fm_name[1], 'distance': 440.0, 'zone': '3'}, 'realTime': str(fmf3pass_time),
                                  'time': str(fmf3pass_time)})
                    fml3pass_time = dt.datetime.strptime(rolling_data.iloc[m_total_pass-3,].starttime[0:14], "%Y%m%d%H%M%S")
                    stops.append({'station': {'key': '0303', 'name': fm_name[2], 'distance': 480.0, 'zone': '3'}, 'realTime': str(fml3pass_time),
                                  'time': str(fml3pass_time)})
                    fmend_time    = dt.datetime.strptime(rolling_data.iloc[m_total_pass-1,].finishtime[0:14], "%Y%m%d%H%M%S")
                    stops.append({'station': {'key': '0304', 'name': fm_name[3], 'distance': 520.0, 'zone': '3'}, 'realTime': str(fmend_time),
                                  'time': str(fmend_time)})




            # for j in range(len(rm_pass_ndarray)):
            #     rm_data = self.marey_data.loc[upids[i]].loc[rm_pass_ndarray[j]]
            #     ## 去除重复道次数据
            #     if rm_data.shape != (31,):
            #         rm_data = self.marey_data.loc[upids[i]].loc[rm_pass_ndarray[j]].iloc[0,]
            #     rm_time = dt.datetime.strptime(rm_data.starttime[0:14], "%Y%m%d%H%M%S")
            #     ## 数据储存
            #     stops.append({'station': {'key': '020' + str(i + 1),
            #                               'name': rm_name[i],
            #                               'distance': (len(fu_name) + i) * 40,
            #                               'zone': '2'},
            #                   'realTime': str(rm_time),
            #                   'time': str(rm_time)})

            # 精轧工序站点时间计算
            # for j in range(len(fm_pass_ndarray)):
            #     fm_data = self.marey_data.loc[upids[i]].loc[fm_pass_ndarray[j]]
            #     ## 去除重复道次数据
            #     if fm_data.shape != (31,):
            #         fm_data = self.marey_data.loc[upids[i]].loc[fm_pass_ndarray[j]].iloc[0,]
            #     fm_time = dt.datetime.strptime(fm_data.starttime[0:14], "%Y%m%d%H%M%S")
            #     ## 数据储存
            #     stops.append({'station': {'key': '030' + str(i + 1),
            #                               # 'name': str(fm_pass_ndarray[i]),
            #                               'distance': (len(fu_name) + len(rm_name) + i) * 40,
            #                               'zone': '3'},
            #                   'realTime': str(fm_time),
            #                   'time': str(fm_time)})

            # 冷却工序站点时间计算
            if int(plate_data.adcontrolcode) <= 0:
                ccTotalTime = 0.0
                mareydata.append({'upid': plate_data.upid,
                                  'slabid': plate_data.slabid,
                                  'toc': str(plate_data.toc),
                                  'steelspec': plate_data.steelspec,
                                  'productcategory': plate_data.productcategory,

                                  'tgtdischargetemp': plate_data.tgtdischargetemp,
                                  'slabthickness': plate_data.slabthickness,
                                  'tgtplatethickness': plate_data.tgtplatethickness,
                                  'tgtwidth': plate_data.tgtwidth,
                                  'tgtplatelength2': plate_data.tgtplatelength2,
                                  'tgttmplatetemp': plate_data.tgttmplatetemp,
                                  'adcontrolcode': plate_data.adcontrolcode,
                                  # 'cooling_start_temp': plate_data.cooling_start_temp,
                                  # 'cooling_stop_temp': plate_data.cooling_stop_temp,
                                  # 'cooling_rate1': plate_data.cooling_rate1,

                                  'stops': stops,
                                  'fuTotalTimeAfter': fuTotalTimeAfter,
                                  'mtotalTime': mtotalTime,
                                  'ccTotalTime': ccTotalTime
                                  })

            else:
                ## cc_start和cc_end时间计算

                if pd.isnull(plate_data.avg_time_b):
                    plate_data.avg_time_b = 0
                if pd.isnull(plate_data.avg_time_w):
                    plate_data.avg_time_w = 0
                cooling_start_time = dt.datetime.strptime(plate_data.timerollingfinish[0:14], "%Y%m%d%H%M%S")
                cc_start = cooling_start_time + dt.timedelta(seconds=plate_data.avg_time_b)
                cc_end = cc_start + dt.timedelta(seconds=plate_data.avg_time_w)

                ## dq_end时间计算
                dq_ratio = plate_data.dq_count / (plate_data.dq_count + plate_data.acc_count)
                if pd.isnull(dq_ratio):
                    dq_ratio = 0
                dq_end = cc_start + (cc_end - cc_start) * dq_ratio
                # cc_start = str(cc_start)[0:19]
                # cc_end = str(cc_end)[0:19]
                ccTotalTime = (cc_end - cc_start).total_seconds()

                ## 数据储存
                stops.append({'station': {'key': '0401',
                                          'name': cc_name[0],
                                          'distance': 560.0,
                                          'zone': '4'},
                              'realTime': str(cc_start)[0:19],
                              'time': str(cc_start)[0:19]})
                stops.append({'station': {'key': '0402',
                                          'name': cc_name[1],
                                          'distance': 600.0,
                                          'zone': '4'},
                              'realTime': str(dq_end)[0:19],
                              'time': str(dq_end)[0:19]})
                stops.append({'station': {'key': '0402',
                                          'name': cc_name[2],
                                          'distance': 640.0,
                                          'zone': '4'},
                              'realTime': str(cc_end)[0:19],
                              'time': str(cc_end)[0:19]})

                if pd.isnull(plate_data.cooling_start_temp) or pd.isnull(plate_data.cooling_stop_temp) or pd.isnull(plate_data.cooling_rate1):
                    plate_data.cooling_start_temp = 0
                    plate_data.cooling_stop_temp = 0
                    plate_data.cooling_rate1 = 0
                # 规格数据、全流程站点数据汇总
                mareydata.append({'upid': plate_data.upid,
                                  'slabid': plate_data.slabid,
                                  'toc': str(plate_data.toc),
                                  'steelspec': plate_data.steelspec,
                                  'productcategory': plate_data.productcategory,

                                  'tgtdischargetemp': plate_data.tgtdischargetemp,
                                  'slabthickness': plate_data.slabthickness,
                                  'tgtplatethickness': plate_data.tgtplatethickness,
                                  'tgtwidth': plate_data.tgtwidth,
                                  'tgtplatelength2': plate_data.tgtplatelength2,
                                  'tgttmplatetemp': plate_data.tgttmplatetemp,
                                  'adcontrolcode': plate_data.adcontrolcode,
                                  'cooling_start_temp': plate_data.cooling_start_temp,
                                  'cooling_stop_temp': plate_data.cooling_stop_temp,
                                  'cooling_rate1': plate_data.cooling_rate1,

                                  'stops': stops,
                                  'fuTotalTimeAfter': fuTotalTimeAfter,
                                  'mtotalTime': mtotalTime,
                                  'ccTotalTime': ccTotalTime
                                  })

        if len(mareydata) < 5:
            return 202, mareydata
        return 200, mareydata
