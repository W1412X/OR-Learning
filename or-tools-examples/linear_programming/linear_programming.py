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

"""展示线性规划 API 用法的示例。"""

from ortools.linear_solver import pywraplp


def Announce(solver, api_type):
    # 打印当前使用的求解器名称与 API 风格的标题信息
    print(
        "---- Linear programming example with " + solver + " (" + api_type + ") -----"
    )


def RunLinearExampleNaturalLanguageAPI(optimization_problem_type):
    """使用自然语言 API 的简单线性规划示例。"""
    # 按给定名称创建底层求解器（GLOP/GLPK_LP/CLP/PDLP/XPRESS_LP）
    solver = pywraplp.Solver.CreateSolver(optimization_problem_type)

    if not solver:
        # 该求解器在当前构建中不可用，直接跳过
        return

    Announce(optimization_problem_type, "natural language API")

    # 正无穷，用作变量上界
    infinity = solver.infinity()
    # x1、x2、x3 是非负连续决策变量（区间 [0, +inf)）
    x1 = solver.NumVar(0.0, infinity, "x1")
    x2 = solver.NumVar(0.0, infinity, "x2")
    x3 = solver.NumVar(0.0, infinity, "x3")

    # 目标函数：最大化 10*x1 + 6*x2 + 4*x3
    solver.Maximize(10 * x1 + 6 * x2 + 4 * x3)
    # 约束 c0：10*x1 + 4*x2 + 5*x3 <= 600（资源限制）
    c0 = solver.Add(10 * x1 + 4 * x2 + 5 * x3 <= 600, "ConstraintName0")
    # 约束 c1：2*x1 + 2*x2 + 6*x3 <= 300（资源限制）
    c1 = solver.Add(2 * x1 + 2 * x2 + 6 * x3 <= 300)
    # 三个变量之和（用于约束 c2 与求解后打印）
    sum_of_vars = sum([x1, x2, x3])
    # 约束 c2：x1 + x2 + x3 <= 100（总产量限制）
    c2 = solver.Add(sum_of_vars <= 100.0, "OtherConstraintName")

    # 求解并打印结果；非 PDLP 求解器（数值精确）时才做解的校验
    SolveAndPrint(
        solver, [x1, x2, x3], [c0, c1, c2], optimization_problem_type != "PDLP"
    )
    # 打印一个线性表达式的解值（x1+x2+x3 的最优取值）
    print("Sum of vars: %s = %s" % (sum_of_vars, sum_of_vars.solution_value()))


def RunLinearExampleCppStyleAPI(optimization_problem_type):
    """使用 C++ 风格 API 的简单线性规划示例。"""
    # 按给定名称创建底层求解器
    solver = pywraplp.Solver.CreateSolver(optimization_problem_type)
    if not solver:
        # 该求解器不可用时直接跳过
        return

    Announce(optimization_problem_type, "C++ style API")

    # 正无穷，用作变量上界
    infinity = solver.infinity()
    # x1、x2、x3 是非负连续决策变量（区间 [0, +inf)）
    x1 = solver.NumVar(0.0, infinity, "x1")
    x2 = solver.NumVar(0.0, infinity, "x2")
    x3 = solver.NumVar(0.0, infinity, "x3")

    # 最大化 10 * x1 + 6 * x2 + 4 * x3
    objective = solver.Objective()
    # 逐个设置目标函数中各变量的系数
    objective.SetCoefficient(x1, 10)
    objective.SetCoefficient(x2, 6)
    objective.SetCoefficient(x3, 4)
    # 指定目标方向为最大化
    objective.SetMaximization()

    # 约束 c0：x1 + x2 + x3 <= 100（总产量限制）
    c0 = solver.Constraint(-infinity, 100.0, "c0")
    # 逐个设置约束中各变量的系数
    c0.SetCoefficient(x1, 1)
    c0.SetCoefficient(x2, 1)
    c0.SetCoefficient(x3, 1)

    # 约束 c1：10 * x1 + 4 * x2 + 5 * x3 <= 600（资源限制）
    c1 = solver.Constraint(-infinity, 600.0, "c1")
    c1.SetCoefficient(x1, 10)
    c1.SetCoefficient(x2, 4)
    c1.SetCoefficient(x3, 5)

    # 约束 c2：2 * x1 + 2 * x2 + 6 * x3 <= 300（资源限制）
    c2 = solver.Constraint(-infinity, 300.0, "c2")
    c2.SetCoefficient(x1, 2)
    c2.SetCoefficient(x2, 2)
    c2.SetCoefficient(x3, 6)

    # 求解并打印结果；非 PDLP 求解器时才做解的校验
    SolveAndPrint(
        solver, [x1, x2, x3], [c0, c1, c2], optimization_problem_type != "PDLP"
    )


def SolveAndPrint(solver, variable_list, constraint_list, is_precise):
    """求解问题并打印解。"""
    # 打印模型规模：变量数与约束数
    print("Number of variables = %d" % solver.NumVariables())
    print("Number of constraints = %d" % solver.NumConstraints())

    # 执行求解
    result_status = solver.Solve()

    # 断言问题存在最优解
    assert result_status == pywraplp.Solver.OPTIMAL

    # 校验解的合理性（使用 GLOP_LINEAR_PROGRAMMING 以外的求解器时，强烈建议验证解！）
    if is_precise:
        assert solver.VerifySolution(1e-7, True)

    # 求解耗时（毫秒）
    print("Problem solved in %f milliseconds" % solver.wall_time())

    # 解的目标函数值
    print("Optimal objective value = %f" % solver.Objective().Value())

    # 解中每个变量的取值
    for variable in variable_list:
        print("%s = %f" % (variable.name(), variable.solution_value()))

    # 进阶用法：迭代次数、检验数（reduced cost）、对偶值（dual value）与约束活跃值
    print("Advanced usage:")
    print("Problem solved in %d iterations" % solver.iterations())
    for variable in variable_list:
        # 每个变量的检验数
        print("%s: reduced cost = %f" % (variable.name(), variable.reduced_cost()))
    # 计算所有约束在最优解处的实际活跃值
    activities = solver.ComputeConstraintActivities()
    for i, constraint in enumerate(constraint_list):
        # 打印每条约束的对偶值（影子价格）与活跃值
        print(
            (
                "constraint %d: dual value = %f\n               activity = %f"
                % (i, constraint.dual_value(), activities[constraint.index()])
            )
        )


def main():
    # 用 5 种求解器分别运行自然语言 API 版本
    RunLinearExampleNaturalLanguageAPI("GLOP")
    RunLinearExampleNaturalLanguageAPI("GLPK_LP")
    RunLinearExampleNaturalLanguageAPI("CLP")
    RunLinearExampleNaturalLanguageAPI("PDLP")
    RunLinearExampleNaturalLanguageAPI("XPRESS_LP")

    # 用 5 种求解器分别运行 C++ 风格 API 版本
    RunLinearExampleCppStyleAPI("GLOP")
    RunLinearExampleCppStyleAPI("GLPK_LP")
    RunLinearExampleCppStyleAPI("CLP")
    RunLinearExampleCppStyleAPI("PDLP")
    RunLinearExampleCppStyleAPI("XPRESS_LP")


if __name__ == "__main__":
    main()
