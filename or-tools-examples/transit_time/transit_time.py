#!/usr/bin/env python
# This Python file uses the following encoding: utf-8
# Copyright 2015 Tin Arm Engineering AB
# Copyright 2018 Google LLC
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""显示路线的行驶时间（Transit Time）。
   距离单位为米，时间单位为分钟。

   曼哈顿平均街区尺寸：750ft x 264ft -> 228m x 80m
   来源：https://nyti.ms/2GDoRIe "NY Times: Know Your distance"
   本示例使用：114m x 80m 的城市街区
"""

from ortools.constraint_solver import pywrapcp


###########################
# 问题数据定义             #
###########################
class Vehicle():
    """存储车辆的属性"""

    def __init__(self):
        """初始化车辆属性"""
        self._capacity = 15
        # 行驶速度：5 km/h，换算为 m/min
        self._speed = 5 * 60 / 3.6

    @property
    def speed(self):
        """获取车辆的平均行驶速度"""
        return self._speed


class CityBlock():
    """城市街区定义"""

    @property
    def width(self):
        """获取街区东西向（West 到 East）的宽度"""
        return 228 / 2

    @property
    def height(self):
        """获取街区南北向（North 到 South）的高度"""
        return 80


class DataProblem():
    """存储问题的数据"""

    def __init__(self):
        """初始化问题数据"""
        self._vehicle = Vehicle()

        # 以"街区数"为单位的地点坐标
        locations = \
                [(4, 4), # 仓库（depot）
                 (2, 0), (8, 0), # 第 0 行
                 (0, 1), (1, 1),
                 (5, 2), (7, 2),
                 (3, 3), (6, 3),
                 (5, 5), (8, 5),
                 (1, 6), (2, 6),
                 (3, 7), (6, 7),
                 (0, 8), (7, 8)]
        # 依据街区实际尺寸，把坐标换算成米
        city_block = CityBlock()
        self._locations = [(loc[0] * city_block.width,
                            loc[1] * city_block.height) for loc in locations]

        # 仓库（起点）在地点列表中的下标
        self._depot = 0

        # 各地点的需求量（仓库为 0）
        self._demands = \
            [0, # depot
             1, 1, # 1, 2
             2, 4, # 3, 4
             2, 4, # 5, 6
             8, 8, # 7, 8
             1, 2, # 9,10
             1, 2, # 11,12
             4, 4, # 13, 14
             8, 8] # 15, 16

        # 各地点的时间窗（最早开始时间, 最晚结束时间）
        self._time_windows = \
            [(0, 0),
             (75, 85), (75, 85), # 1, 2
             (60, 70), (45, 55), # 3, 4
             (0, 8), (50, 60), # 5, 6
             (0, 10), (10, 20), # 7, 8
             (0, 10), (75, 85), # 9, 10
             (85, 95), (5, 15), # 11, 12
             (15, 25), (10, 20), # 13, 14
             (45, 55), (30, 40)] # 15, 16

    @property
    def vehicle(self):
        """获取一辆车"""
        return self._vehicle

    @property
    def locations(self):
        """获取所有地点坐标"""
        return self._locations

    @property
    def num_locations(self):
        """获取地点数量"""
        return len(self.locations)

    @property
    def depot(self):
        """获取仓库的下标"""
        return self._depot

    @property
    def demands(self):
        """获取各地点的需求量"""
        return self._demands

    @property
    def time_per_demand_unit(self):
        """获取装载单位需求所需的时间（分钟）"""
        return 5  # 每单位需求 5 分钟

    @property
    def time_windows(self):
        """获取各地点的时间窗（开始时间, 结束时间）"""
        return self._time_windows


#######################
# 问题约束与计算        #
#######################
def manhattan_distance(position_1, position_2):
    """计算两个点之间的曼哈顿距离"""
    return (
        abs(position_1[0] - position_2[0]) + abs(position_1[1] - position_2[1]))


class CreateTimeEvaluator(object):
    """创建回调，获取地点之间的总时间（服务时间 + 行驶时间）。"""

    @staticmethod
    def service_time(data, node):
        """获取指定地点的服务时间（需求量 x 单位装载时间）。"""
        return data.demands[node] * data.time_per_demand_unit

    @staticmethod
    def travel_time(data, from_node, to_node):
        """获取两个地点之间的行驶时间（曼哈顿距离 / 车速）。"""
        if from_node == to_node:
            travel_time = 0
        else:
            travel_time = manhattan_distance(data.locations[
                from_node], data.locations[to_node]) / data.vehicle.speed
        return travel_time

    def __init__(self, data):
        """初始化总时间矩阵。"""
        self._total_time = {}
        # 预先计算总时间矩阵，使时间回调的查询复杂度为 O(1)
        for from_node in range(data.num_locations):
            self._total_time[from_node] = {}
            for to_node in range(data.num_locations):
                if from_node == to_node:
                    self._total_time[from_node][to_node] = 0
                else:
                    # 总时间 = 出发地的服务时间 + 两地间的行驶时间（取整）
                    self._total_time[from_node][to_node] = int(
                        self.service_time(data, from_node) + self.travel_time(
                            data, from_node, to_node))

    def time_evaluator(self, from_node, to_node):
        """返回两个节点之间的总时间"""
        return self._total_time[from_node][to_node]


def print_transit_time(route, time_evaluator):
    """打印一条路线中相邻节点之间的经过时间"""
    total_time = 0
    for i, j in route:
        total_time += time_evaluator(i, j)
        print('{0} -> {1}: {2}min'.format(i, j, time_evaluator(i, j)))
    print('Total time: {0}min\n'.format(total_time))


########
# 主函数 #
########
def main():
    """程序入口"""
    # 实例化问题数据。
    data = DataProblem()

    # 打印各路线的经过时间
    time_evaluator = CreateTimeEvaluator(data).time_evaluator
    print('Route 0:')
    print_transit_time([[0, 5], [5, 8], [8, 6], [6, 2], [2, 0]], time_evaluator)

    print('Route 1:')
    print_transit_time([[0, 9], [9, 14], [14, 16], [16, 10], [10, 0]],
                       time_evaluator)

    print('Route 2:')
    print_transit_time([[0, 12], [12, 13], [13, 15], [15, 11], [11, 0]],
                       time_evaluator)

    print('Route 3:')
    print_transit_time([[0, 7], [7, 4], [4, 3], [3, 1], [1, 0]], time_evaluator)


if __name__ == '__main__':
    main()
