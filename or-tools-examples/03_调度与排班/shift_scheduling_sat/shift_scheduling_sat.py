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

"""构建一个员工轮班排班问题并求解。"""

from absl import app
from absl import flags

from ortools.sat.python import cp_model

_OUTPUT_PROTO = flags.DEFINE_string(
    "output_proto", "", "Output file to write the cp_model proto to."
)
_PARAMS = flags.DEFINE_string(
    "params", "max_time_in_seconds:10.0", "Sat solver parameters."
)


def negated_bounded_span(
    works: list[cp_model.BoolVarT], start: int, length: int
) -> list[cp_model.BoolVarT]:
    """过滤掉被赋值为 True 的孤立连续子序列。

    提取布尔变量区间 [start, start + length) 并取反；
    若区间左/右还有其他变量，则用它们（不取反）包围该区间。

    参数：
      works: 从中提取区间的变量列表。
      start: 区间的起始位置。
      length: 区间的长度。

    返回：
      一个变量列表：当该子序列全为 True（且被 False 变量或 works 的
      首/尾正确包围）时，其合取结果为 False。
    """
    sequence = []
    # 左边界（works 的开头，或 works[start - 1]）
    if start > 0:
        sequence.append(works[start - 1])
    for i in range(length):
        sequence.append(~works[start + i])
    # 右边界（works 的结尾，或 works[start + length]）
    if start + length < len(works):
        sequence.append(works[start + length])
    return sequence


def add_soft_sequence_constraint(
    model: cp_model.CpModel,
    works: list[cp_model.BoolVarT],
    hard_min: int,
    soft_min: int,
    min_cost: int,
    soft_max: int,
    hard_max: int,
    max_cost: int,
    prefix: str,
) -> tuple[list[cp_model.BoolVarT], list[int]]:
    """对取值为真的变量施加带软/硬边界的连续序列约束。

    本约束考察每个极长的连续为真片段：禁止长度 < hard_min 或 > hard_max
    的连续段；当长度 < soft_min 或 > soft_max 时生成罚分项。

    参数：
      model: 连续序列约束构建在该模型上。
      works: 布尔变量列表。
      hard_min: 任何连续为真的序列长度必须 ≥ hard_min。
      soft_min: 任何序列长度应 ≥ soft_min，否则按差值线性罚分加入目标。
      min_cost: 长度小于 soft_min 时线性罚分的系数。
      soft_max: 任何序列长度应 ≤ soft_max，否则按差值线性罚分加入目标。
      hard_max: 任何连续为真的序列长度必须 ≤ hard_max。
      max_cost: 长度大于 soft_max 时线性罚分的系数。
      prefix: 罚分字面量的基础名称。

    返回：
      一个元组 (变量列表, 系数列表)，包含该序列约束生成的各类罚分。
    """
    cost_literals = []
    cost_coefficients = []

    # 禁止过短的连续序列。
    for length in range(1, hard_min):
        for start in range(len(works) - length + 1):
            model.add_bool_or(negated_bounded_span(works, start, length))

    # 对低于软下界的序列进行罚分。
    if min_cost > 0:
        for length in range(hard_min, soft_min):
            for start in range(len(works) - length + 1):
                span = negated_bounded_span(works, start, length)
                name = f": under_span(start={start}, length={length})"
                lit = model.new_bool_var(prefix + name)
                span.append(lit)
                model.add_bool_or(span)
                cost_literals.append(lit)
                # 恰好过滤出该长度的短序列：
                # 罚分与距离 soft_min 的差值成正比。
                cost_coefficients.append(min_cost * (soft_min - length))

    # 对高于软上界的序列进行罚分。
    if max_cost > 0:
        for length in range(soft_max + 1, hard_max + 1):
            for start in range(len(works) - length + 1):
                span = negated_bounded_span(works, start, length)
                name = f": over_span(start={start}, length={length})"
                lit = model.new_bool_var(prefix + name)
                span.append(lit)
                model.add_bool_or(span)
                cost_literals.append(lit)
                # 支付的成本 = max_cost × 超出的长度。
                cost_coefficients.append(max_cost * (length - soft_max))

    # 直接禁止长度为 hard_max + 1 的连续为真序列
    for start in range(len(works) - hard_max):
        model.add_bool_or([~works[i] for i in range(start, start + hard_max + 1)])
    return cost_literals, cost_coefficients


def add_soft_sum_constraint(
    model: cp_model.CpModel,
    works: list[cp_model.BoolVarT],
    hard_min: int,
    soft_min: int,
    min_cost: int,
    soft_max: int,
    hard_max: int,
    max_cost: int,
    prefix: str,
) -> tuple[list[cp_model.IntVar], list[int]]:
    """带软/硬边界的求和约束。

    本约束统计 works 中取值为真的变量个数：
    禁止总和 < hard_min 或 > hard_max；
    当总和 < soft_min 或 > soft_max 时生成罚分项。

    参数：
      model: 约束构建在该模型上。
      works: 布尔变量列表。
      hard_min: 总和必须 ≥ hard_min。
      soft_min: 总和应 ≥ soft_min，否则按差值线性罚分加入目标。
      min_cost: 总和小于 soft_min 时线性罚分的系数。
      soft_max: 总和应 ≤ soft_max，否则按差值线性罚分加入目标。
      hard_max: 总和必须 ≤ hard_max。
      max_cost: 总和大于 soft_max 时线性罚分的系数。
      prefix: 罚分变量的基础名称。

    返回：
      一个元组 (变量列表, 系数列表)，包含该约束生成的各类罚分。
    """
    cost_variables = []
    cost_coefficients = []
    sum_var = model.new_int_var(hard_min, hard_max, "")
    # 通过 sum_var 的取值域施加硬性求和约束。
    model.add(sum_var == sum(works))

    # 对低于 soft_min 目标的总和进行罚分。
    if soft_min > hard_min and min_cost > 0:
        delta = model.new_int_var(-len(works), len(works), "")
        model.add(delta == soft_min - sum_var)
        # TODO(user): 与只用 excess >= soft_min - sum_var 的写法比较效率。
        excess = model.new_int_var(0, 7, prefix + ": under_sum")
        model.add_max_equality(excess, [delta, 0])
        cost_variables.append(excess)
        cost_coefficients.append(min_cost)

    # 对高于 soft_max 目标的总和进行罚分。
    if soft_max < hard_max and max_cost > 0:
        delta = model.new_int_var(-7, 7, "")
        model.add(delta == sum_var - soft_max)
        excess = model.new_int_var(0, 7, prefix + ": over_sum")
        model.add_max_equality(excess, [delta, 0])
        cost_variables.append(excess)
        cost_coefficients.append(max_cost)

    return cost_variables, cost_coefficients


def solve_shift_scheduling(params: str, output_proto: str):
    """求解员工轮班排班问题。"""
    # 数据
    num_employees = 8
    num_weeks = 3
    shifts = ["O", "M", "A", "N"]

    # 固定排班：(员工, 班次, 日期)。
    # 这里固定了排班表的前 2 天。
    fixed_assignments = [
        (0, 0, 0),
        (1, 0, 0),
        (2, 1, 0),
        (3, 1, 0),
        (4, 2, 0),
        (5, 2, 0),
        (6, 2, 3),
        (7, 3, 0),
        (0, 1, 1),
        (1, 1, 1),
        (2, 2, 1),
        (3, 2, 1),
        (4, 2, 1),
        (5, 0, 1),
        (6, 0, 1),
        (7, 3, 1),
    ]

    # 员工请求：(员工, 班次, 日期, 权重)。
    # 负权重表示员工希望获得该班次安排。
    requests = [
        # 员工 3 不想在第一个周六上班（对休息班次给负权重）。
        (3, 0, 5, -2),
        # 员工 5 想要第二个周四的夜班（负权重）。
        (5, 3, 10, -2),
        # 员工 2 不想要第一个周五的夜班（正权重）。
        (2, 3, 4, 4),
    ]

    # 班次的连续序列约束：
    #     (班次, 硬下界, 软下界, 下界罚分,
    #             软上界, 硬上界, 上界罚分)
    shift_constraints = [
        # 休息必须连续 1 或 2 天，这是硬性约束。
        (0, 1, 1, 0, 2, 2, 0),
        # 夜班连续 2~3 天为宜；连续 1 或 4 天也可接受但要罚分。
        (3, 1, 2, 20, 3, 4, 5),
    ]

    # 班次天数的每周总和约束：
    #     (班次, 硬下界, 软下界, 下界罚分,
    #             软上界, 硬上界, 上界罚分)
    weekly_sum_constraints = [
        # 每周休息天数的约束。
        (0, 1, 2, 7, 2, 3, 4),
        # 每周至少 1 个夜班（违反则罚分）；至多 4 个（硬性）。
        (3, 0, 1, 3, 4, 4, 0),
    ]

    # 受罚的班次转换：
    #     (前一班次, 后一班次, 罚分（0 表示禁止）)
    penalized_transitions = [
        # 中班转夜班罚 4 分。
        (2, 3, 4),
        # 夜班转早班被禁止。
        (3, 1, 0),
    ]

    # 各工作班次（早、中、晚）每天的人力需求，从周一开始
    weekly_cover_demands = [
        (2, 3, 1),  # 周一
        (2, 3, 1),  # 周二
        (2, 2, 2),  # 周三
        (2, 3, 1),  # 周四
        (2, 2, 2),  # 周五
        (1, 2, 3),  # 周六
        (1, 3, 1),  # 周日
    ]

    # 每种班次超出覆盖需求的罚分系数。
    excess_cover_penalties = (2, 2, 5)

    num_days = num_weeks * 7
    num_shifts = len(shifts)

    model = cp_model.CpModel()

    # 决策变量：work[e, s, d] = 员工 e 在第 d 天上班次 s
    work = {}
    for e in range(num_employees):
        for s in range(num_shifts):
            for d in range(num_days):
                work[e, s, d] = model.new_bool_var(f"work{e}_{s}_{d}")

    # 目标函数中的线性项（最小化场景）。
    obj_int_vars: list[cp_model.IntVar] = []
    obj_int_coeffs: list[int] = []
    obj_bool_vars: list[cp_model.BoolVarT] = []
    obj_bool_coeffs: list[int] = []

    # 每人每天恰好一个班次。
    for e in range(num_employees):
        for d in range(num_days):
            model.add_exactly_one(work[e, s, d] for s in range(num_shifts))

    # 固定排班。
    for e, s, d in fixed_assignments:
        model.add(work[e, s, d] == 1)

    # 员工请求（作为带权目标项）
    for e, s, d, w in requests:
        obj_bool_vars.append(work[e, s, d])
        obj_bool_coeffs.append(w)

    # 班次连续序列约束
    for ct in shift_constraints:
        shift, hard_min, soft_min, min_cost, soft_max, hard_max, max_cost = ct
        for e in range(num_employees):
            works = [work[e, shift, d] for d in range(num_days)]
            variables, coeffs = add_soft_sequence_constraint(
                model,
                works,
                hard_min,
                soft_min,
                min_cost,
                soft_max,
                hard_max,
                max_cost,
                f"shift_constraint(employee {e}, shift {shift})",
            )
            obj_bool_vars.extend(variables)
            obj_bool_coeffs.extend(coeffs)

    # 每周总和约束
    for ct in weekly_sum_constraints:
        shift, hard_min, soft_min, min_cost, soft_max, hard_max, max_cost = ct
        for e in range(num_employees):
            for w in range(num_weeks):
                works = [work[e, shift, d + w * 7] for d in range(7)]
                variables, coeffs = add_soft_sum_constraint(
                    model,
                    works,
                    hard_min,
                    soft_min,
                    min_cost,
                    soft_max,
                    hard_max,
                    max_cost,
                    f"weekly_sum_constraint(employee {e}, shift {shift}, week {w})",
                )
                obj_int_vars.extend(variables)
                obj_int_coeffs.extend(coeffs)

    # 受罚的班次转换
    for previous_shift, next_shift, cost in penalized_transitions:
        for e in range(num_employees):
            for d in range(num_days - 1):
                transition = [
                    ~work[e, previous_shift, d],
                    ~work[e, next_shift, d + 1],
                ]
                if cost == 0:
                    model.add_bool_or(transition)
                else:
                    trans_var = model.new_bool_var(
                        f"transition (employee={e}, day={d})"
                    )
                    transition.append(trans_var)
                    model.add_bool_or(transition)
                    obj_bool_vars.append(trans_var)
                    obj_bool_coeffs.append(cost)

    # 覆盖约束
    for s in range(1, num_shifts):
        for w in range(num_weeks):
            for d in range(7):
                works = [work[e, s, w * 7 + d] for e in range(num_employees)]
                # 忽略休息班次。
                min_demand = weekly_cover_demands[d][s - 1]
                worked = model.new_int_var(min_demand, num_employees, "")
                model.add(worked == sum(works))
                over_penalty = excess_cover_penalties[s - 1]
                if over_penalty > 0:
                    name = f"excess_demand(shift={s}, week={w}, day={d})"
                    excess = model.new_int_var(0, num_employees - min_demand, name)
                    model.add(excess == worked - min_demand)
                    obj_int_vars.append(excess)
                    obj_int_coeffs.append(over_penalty)

    # 目标函数：所有布尔罚分与整数罚分的加权和最小化
    model.minimize(
        sum(obj_bool_vars[i] * obj_bool_coeffs[i] for i in range(len(obj_bool_vars)))
        + sum(obj_int_vars[i] * obj_int_coeffs[i] for i in range(len(obj_int_vars)))
    )

    if output_proto:
        print(f"Writing proto to {output_proto}")
        with open(output_proto, "w") as text_file:
            text_file.write(str(model))

    # 求解模型。
    solver = cp_model.CpSolver()
    if params:
        solver.parameters.parse_text_format(params)
    solution_printer = cp_model.ObjectiveSolutionPrinter()
    status = solver.solve(model, solution_printer)

    # 打印解。
    if status == cp_model.OPTIMAL or status == cp_model.FEASIBLE:
        print()
        header = "          "
        for w in range(num_weeks):
            header += "M T W T F S S "
        print(header)
        for e in range(num_employees):
            schedule = ""
            for d in range(num_days):
                for s in range(num_shifts):
                    if solver.boolean_value(work[e, s, d]):
                        schedule += shifts[s] + " "
            print(f"worker {e}: {schedule}")
        print()
        print("Penalties:")
        for i, var in enumerate(obj_bool_vars):
            if solver.boolean_value(var):
                penalty = obj_bool_coeffs[i]
                if penalty > 0:
                    print(f"  {var.name} violated, penalty={penalty}")
                else:
                    print(f"  {var.name} fulfilled, gain={-penalty}")

        for i, var in enumerate(obj_int_vars):
            if solver.value(var) > 0:
                print(
                    f"  {var.name} violated by {solver.value(var)}, linear"
                    f" penalty={obj_int_coeffs[i]}"
                )

    print()
    print(solver.response_stats())


def main(_):
    solve_shift_scheduling(_PARAMS.value, _OUTPUT_PROTO.value)


if __name__ == "__main__":
    app.run(main)
