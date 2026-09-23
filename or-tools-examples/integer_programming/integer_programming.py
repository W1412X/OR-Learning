#!/usr/bin/env python3
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

"""演示整数规划 API 用法的示例。"""

from ortools.linear_solver import pywraplp


def Announce(solver, api_type):
    # 打印示例标题横幅（求解器名称 + API 风格）。
    print(
        "---- Integer programming example with " + solver + " (" + api_type + ") -----"
    )


def RunIntegerExampleNaturalLanguageAPI(optimization_problem_type):
    """用自然语言风格 API 求解简单整数规划示例。"""

    # 按求解器名称创建线性求解器封装；不可用时直接跳过。
    solver = pywraplp.Solver.CreateSolver(optimization_problem_type)
    if not solver:
        return

    Announce(optimization_problem_type, "natural language API")

    infinity = solver.infinity()
    # x1 与 x2 是非负整数变量。
    x1 = solver.IntVar(0.0, infinity, "x1")
    x2 = solver.IntVar(0.0, infinity, "x2")

    # 目标函数：最小化 x1 + 2 * x2。
    solver.Minimize(x1 + 2 * x2)
    # 约束条件：3 * x1 + 2 * x2 >= 17。
    solver.Add(3 * x1 + 2 * x2 >= 17)

    # 求解并打印结果。
    SolveAndPrint(solver, [x1, x2])


def RunIntegerExampleCppStyleAPI(optimization_problem_type):
    """用 C++ 风格 API 求解简单整数规划示例。"""
    # 按求解器名称创建线性求解器封装；不可用时直接跳过。
    solver = pywraplp.Solver.CreateSolver(optimization_problem_type)
    if not solver:
        return

    Announce(optimization_problem_type, "C++ style API")

    infinity = solver.infinity()
    # x1 与 x2 是非负整数变量。
    x1 = solver.IntVar(0.0, infinity, "x1")
    x2 = solver.IntVar(0.0, infinity, "x2")

    # 最小化 x1 + 2 * x2。
    objective = solver.Objective()
    objective.SetCoefficient(x1, 1)
    objective.SetCoefficient(x2, 2)

    # 约束：3 * x1 + 2 * x2 >= 17。
    ct = solver.Constraint(17, infinity)
    ct.SetCoefficient(x1, 3)
    ct.SetCoefficient(x2, 2)

    # 求解并打印结果。
    SolveAndPrint(solver, [x1, x2])


def SolveAndPrint(solver, variable_list):
    """求解问题并打印解。"""
    # 打印模型规模信息。
    print("Number of variables = %d" % solver.NumVariables())
    print("Number of constraints = %d" % solver.NumConstraints())

    # 执行求解。
    result_status = solver.Solve()

    # 断言问题有最优解。
    assert result_status == pywraplp.Solver.OPTIMAL

    # 校验解的合法性（使用 GLOP_LINEAR_PROGRAMMING 以外的求解器时，
    # 强烈建议校验解！）。
    assert solver.VerifySolution(1e-7, True)

    # 打印求解耗时。
    print("Problem solved in %f milliseconds" % solver.wall_time())

    # 打印解的目标函数值。
    print("Optimal objective value = %f" % solver.Objective().Value())

    # 打印解中每个变量的取值。
    for variable in variable_list:
        print("%s = %f" % (variable.name(), variable.solution_value()))

    # 打印进阶信息：分支定界节点数。
    print("Advanced usage:")
    print("Problem solved in %d branch-and-bound nodes" % solver.nodes())


def RunAllIntegerExampleNaturalLanguageAPI():
    # 依次在多个后端求解器上运行自然语言风格 API 示例。
    RunIntegerExampleNaturalLanguageAPI("GLPK")
    # 由于 CBC 存在 ASAN 错误，已禁用。
    # RunIntegerExampleNaturalLanguageAPI('CBC')
    RunIntegerExampleNaturalLanguageAPI("SCIP")
    RunIntegerExampleNaturalLanguageAPI("SAT")
    RunIntegerExampleNaturalLanguageAPI("XPRESS")


def RunAllIntegerExampleCppStyleAPI():
    # 依次在多个后端求解器上运行 C++ 风格 API 示例。
    RunIntegerExampleCppStyleAPI("GLPK")
    # 由于 CBC 存在 ASAN 错误，已禁用。
    # RunIntegerExampleCppStyleAPI('CBC')
    RunIntegerExampleCppStyleAPI("SCIP")
    RunIntegerExampleCppStyleAPI("SAT")
    RunIntegerExampleCppStyleAPI("XPRESS")


def main():
    # 先运行自然语言风格 API 的全部示例，再运行 C++ 风格 API 的全部示例。
    RunAllIntegerExampleNaturalLanguageAPI()
    RunAllIntegerExampleCppStyleAPI()


if __name__ == "__main__":
    main()
