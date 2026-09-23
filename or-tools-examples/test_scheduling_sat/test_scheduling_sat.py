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

"""求解一个测试调度问题。

测试必须由操作员执行。每个测试有时长和功率消耗。

操作员从电源取电。操作员与电源之间的对应关系是给定的。

电源有可输出的最大功率上限。

能否对测试进行排程，使得每个电源的功率消耗始终低于其最大功率，并且总工期
（makespan）最短？
"""

from collections.abc import Sequence
import io
from typing import Dict, Tuple

from absl import app
from absl import flags
import pandas as pd

from ortools.sat.python import cp_model

# CP-SAT 求解器参数（文本格式）。
_PARAMS = flags.DEFINE_string(
    "params",
    "num_search_workers:16,log_search_progress:true,max_time_in_seconds:45",
    "Sat solver parameters.",
)


def build_data() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """构建数据表。"""
    # 测试数据表：名称、操作员、时长、平均功率。
    tests_str = """
  Name Operator    TestTime    AveragePower
   T1     O1           300            200
   T2     O1           150             40
   T3     O2           100             65
   T4     O2           250            150
   T5     O3           210            140
  """

    # 操作员与电源的对应关系表。
    operators_str = """
  Operator Supply
      O1      S1
      O2      S2
      O3      S2
  """

    # 电源的最大允许功率表。
    supplies_str = """
  Supply  MaxAllowedPower
   S1        230
   S2        210
  """

    tests_data = pd.read_table(io.StringIO(tests_str), sep=r"\s+")
    operators_data = pd.read_table(io.StringIO(operators_str), sep=r"\s+")
    supplies_data = pd.read_table(io.StringIO(supplies_str), sep=r"\s+")

    return (tests_data, operators_data, supplies_data)


def solve(
    tests_data: pd.DataFrame,
    operator_data: pd.DataFrame,
    supplies_data: pd.DataFrame,
) -> None:
    """求解测试调度问题。"""

    # 解析数据：操作员 → 电源 的映射。
    operator_to_supply: Dict[str, str] = {}
    for _, row in operator_data.iterrows():
        operator_to_supply[row["Operator"]] = row["Supply"]

    # 解析数据：电源 → 最大允许功率 的映射。
    supply_to_max_power: Dict[str, int] = {}
    for _, row in supplies_data.iterrows():
        supply_to_max_power[row["Supply"]] = row["MaxAllowedPower"]

    # 时间视界：所有测试时长之和（安全的松弛上界）。
    horizon = tests_data["TestTime"].sum()

    # OR-Tools 模型。
    model = cp_model.CpModel()

    # 创建各类容器。
    # 按电源分组的（区间变量列表, 功率需求列表）。
    tests_per_supply: Dict[str, Tuple[list[cp_model.IntervalVar], list[int]]] = {}
    # 测试 → 电源 的映射。
    test_supply: Dict[str, str] = {}
    # 各测试的开始时间变量。
    test_starts: Dict[str, cp_model.IntVar] = {}
    # 各测试的时长。
    test_durations: Dict[str, int] = {}
    # 各测试的功率。
    test_powers: Dict[str, int] = {}
    # 所有测试的结束时间（用于 makespan 约束）。
    all_ends = []

    # 为每个测试创建区间变量。
    for _, row in tests_data.iterrows():
        name: str = row["Name"]
        operator: str = row["Operator"]
        test_time: int = row["TestTime"]
        average_power: int = row["AveragePower"]
        supply: str = operator_to_supply[operator]

        # 决策变量：测试的开始时间（时长固定，故上界为 horizon - test_time）。
        start = model.new_int_var(0, horizon - test_time, f"start_{name}")
        # 定长区间变量：由开始时间与固定时长构成。
        interval = model.new_fixed_size_interval_var(
            start, test_time, f"interval_{name}"
        )

        # 记录信息。
        test_starts[name] = start
        test_durations[name] = test_time
        test_powers[name] = average_power
        test_supply[name] = supply
        if supply not in tests_per_supply.keys():
            tests_per_supply[supply] = ([], [])
        # 将测试按电源分组：区间与功率需求。
        tests_per_supply[supply][0].append(interval)
        tests_per_supply[supply][1].append(average_power)
        # 结束时间 = 开始时间 + 时长。
        all_ends.append(start + test_time)

    # 约束：为每个电源创建累积资源约束（功率不超过电源最大功率）。
    for supply, (intervals, demands) in tests_per_supply.items():
        model.add_cumulative(intervals, demands, supply_to_max_power[supply])

    # 目标：makespan 不小于任何测试的结束时间。
    makespan = model.new_int_var(0, horizon, "makespan")
    for end in all_ends:
        model.add(makespan >= end)
    # 最小化总工期。
    model.minimize(makespan)

    # 求解模型。
    solver = cp_model.CpSolver()
    if _PARAMS.value:
        solver.parameters.parse_text_format(_PARAMS.value)
    status = solver.solve(model)

    # 报告解。
    if status == cp_model.OPTIMAL or status == cp_model.FEASIBLE:
        print(f"Makespan = {solver.value(makespan)}")
        for name, start in test_starts.items():
            print(
                f"{name}: start:{solver.value(start)} duration:{test_durations[name]}"
                f" power:{test_powers[name]} on supply {test_supply[name]}"
            )


def main(argv: Sequence[str]) -> None:
    """构建数据并求解调度问题。"""
    if len(argv) > 1:
        raise app.UsageError("Too many command-line arguments.")

    tests_data, operators_data, supplies_data = build_data()
    print("Tests data")
    print(tests_data)
    print()
    print("Operators data")
    print(operators_data)
    print()
    print("Supplies data")
    print(supplies_data)

    solve(tests_data, operators_data, supplies_data)


if __name__ == "__main__":
    app.run(main)
