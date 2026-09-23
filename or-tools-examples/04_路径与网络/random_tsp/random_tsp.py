# Copyright 2010-2025 Google LLC
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
"""旅行商问题（TSP）示例。

   本示例使用 routing 库的 Python 封装来求解一个旅行商问题。
   问题的描述参见：
   http://en.wikipedia.org/wiki/Travelling_salesman_problem。
   求解引擎使用局部搜索（local search）改进解，
   初始解由"最廉价弧添加"（cheapest addition）启发式生成。
   还可以随机禁止节点之间的若干连接（forbidden arcs，禁止弧）。
"""

import argparse
from functools import partial
import random

from ortools.constraint_solver import routing_enums_pb2
from ortools.constraint_solver import pywrapcp

# 命令行参数解析器（argparse）
parser = argparse.ArgumentParser()

parser.add_argument(
    '--tsp_size',
    default=10,
    type=int,
    help='Size of Traveling Salesman Problem instance.')
parser.add_argument(
    '--tsp_use_random_matrix',
    default=True,
    type=bool,
    help='Use random cost matrix.')
parser.add_argument(
    '--tsp_random_forbidden_connections',
    default=0,
    type=int,
    help='Number of random forbidden connections.')
parser.add_argument(
    '--tsp_random_seed', default=0, type=int, help='Random seed.')

# 成本/距离函数。


def Distance(manager, i, j):
    """演示用距离函数。"""
    # 在此处填入你自己的距离计算代码。
    # Routing 库的回调参数是内部索引，需先转换回原始节点编号
    node_i = manager.IndexToNode(i)
    node_j = manager.IndexToNode(j)
    return node_i + node_j


class RandomMatrix(object):
    """随机成本矩阵。"""

    def __init__(self, size, seed):
        """初始化随机矩阵。"""

        # 使用给定种子创建随机数生成器，保证结果可复现
        rand = random.Random()
        rand.seed(seed)
        # 距离上限：随机距离取值范围为 0~99
        distance_max = 100
        # 生成 size×size 的矩阵：对角线为 0，其余为随机整数
        self.matrix = {}
        for from_node in range(size):
            self.matrix[from_node] = {}
            for to_node in range(size):
                if from_node == to_node:
                    self.matrix[from_node][to_node] = 0
                else:
                    self.matrix[from_node][to_node] = rand.randrange(
                        distance_max)

    def Distance(self, manager, from_index, to_index):
        # 查表返回两个节点间的距离（内部索引先转回节点编号）
        return self.matrix[manager.IndexToNode(from_index)][manager.IndexToNode(
            to_index)]


def main(args):
    # 创建路径规划模型
    if args.tsp_size > 0:
        # 规模为 args.tsp_size 的 TSP
        # 第二个参数 = 1 表示只构建一条路径（这正是 TSP）。
        # 节点编号从 0 到 args_tsp_size - 1，路径起点默认为节点 0。
        manager = pywrapcp.RoutingIndexManager(args.tsp_size, 1, 0)
        routing = pywrapcp.RoutingModel(manager)
        # 使用默认路由搜索参数
        search_parameters = pywrapcp.DefaultRoutingSearchParameters()
        # 设置首解启发式策略（最廉价弧添加，PATH_CHEAPEST_ARC）。
        search_parameters.first_solution_strategy = (
            routing_enums_pb2.FirstSolutionStrategy.PATH_CHEAPEST_ARC)

        # 设置成本函数。
        # 在此注册距离访问回调：回调接收两个参数（起点和终点的内部索引），
        # 返回这两个索引之间的距离。
        cost = 0
        if args.tsp_use_random_matrix:
            # 随机矩阵模式：注册 RandomMatrix.Distance 回调
            matrix = RandomMatrix(args.tsp_size, args.tsp_random_seed)
            cost = routing.RegisterTransitCallback(
                partial(matrix.Distance, manager))
        else:
            # 演示模式：注册简单距离函数 Distance 回调
            cost = routing.RegisterTransitCallback(partial(Distance, manager))
        # 将回调设为所有车辆的弧成本评估器（目标函数来源）
        routing.SetArcCostEvaluatorOfAllVehicles(cost)
        # （随机地）禁止某些节点连接。
        rand = random.Random()
        rand.seed(args.tsp_random_seed)
        forbidden_connections = 0
        # 循环随机挑选"起点→终点"，从下一跳变量的取值域中移除，
        # 直到成功禁用 args.tsp_random_forbidden_connections 条连接
        while forbidden_connections < args.tsp_random_forbidden_connections:
            from_node = rand.randrange(args.tsp_size - 1)
            to_node = rand.randrange(args.tsp_size - 1) + 1
            if routing.NextVar(from_node).Contains(to_node):
                print('Forbidding connection ' + str(from_node) + ' -> ' +
                      str(to_node))
                # 移除取值即禁止从 from_node 直接到 to_node
                routing.NextVar(from_node).RemoveValue(to_node)
                forbidden_connections += 1

        # 求解；若存在解则返回 assignment
        assignment = routing.Solve()
        if assignment:
            # 解的总成本（目标值）
            print(assignment.ObjectiveValue())
            # 检查解。
            # 本例只有一条路径；若是多车辆问题，需从 0 遍历到 routing.vehicles() - 1
            route_number = 0
            node = routing.Start(route_number)
            route = ''
            # 沿"下一跳"变量逐节点前进，直到路径终点
            while not routing.IsEnd(node):
                route += str(node) + ' -> '
                node = assignment.Value(routing.NextVar(node))
            route += '0'
            print(route)
        else:
            print('No solution found.')
    else:
        print('Specify an instance greater than 0.')


if __name__ == '__main__':
    main(parser.parse_args())
