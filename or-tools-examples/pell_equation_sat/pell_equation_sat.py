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

"""求解佩尔方程 x^2 - coeff * y^2 = 1。"""

from collections.abc import Sequence

from absl import app
from absl import flags

from ortools.sat.python import cp_model


# 命令行参数：佩尔方程的系数。
_COEFF = flags.DEFINE_integer("coeff", 1, "The Pell equation coefficient.")
# 命令行参数：变量允许的最大取值。
_MAX_VALUE = flags.DEFINE_integer("max_value", 5000_000, "The maximum value.")


def solve_pell(coeff: int, max_value: int) -> None:
    """求解佩尔方程 x^2 - coeff * y^2 = 1。"""
    model = cp_model.CpModel()

    # 决策变量 x、y：正整数解，取值范围 [1, max_value]。
    x = model.new_int_var(1, max_value, "x")
    y = model.new_int_var(1, max_value, "y")

    # 佩尔方程：x^2 - coeff * y^2 = 1
    # 用辅助变量 x_square、y_square 分别表示 x*x 与 y*y。
    x_square = model.new_int_var(1, max_value * max_value, "x_square")
    y_square = model.new_int_var(1, max_value * max_value, "y_square")
    # 乘积约束：x_square == x * x（表达平方项的非线性约束）。
    model.add_multiplication_equality(x_square, x, x)
    # 乘积约束：y_square == y * y。
    model.add_multiplication_equality(y_square, y, y)
    # 核心方程约束：x^2 - coeff * y^2 == 1。
    model.add(x_square - coeff * y_square == 1)

    # 自定义搜索决策策略：优先选择剩余取值最少的变量，并从最小值开始尝试，
    # 有助于尽快找到最小的正整数解。
    model.add_decision_strategy(
        [x, y], cp_model.CHOOSE_MIN_DOMAIN_SIZE, cp_model.SELECT_MIN_VALUE
    )

    solver = cp_model.CpSolver()
    # 求解器参数：并行 worker 数量、搜索日志、模型预求解、关闭探测。
    solver.parameters.num_workers = 12
    solver.parameters.log_search_progress = True
    solver.parameters.cp_model_presolve = True
    solver.parameters.cp_model_probing_level = 0

    # 求解模型。
    result = solver.solve(model)
    if result == cp_model.OPTIMAL:
        print(f"x={solver.value(x)} y={solver.value(y)} coeff={coeff}")
        # 校验解确实满足佩尔方程，否则视为求解错误。
        if solver.value(x) ** 2 - coeff * (solver.value(y) ** 2) != 1:
            raise ValueError("Pell equation not satisfied.")


def main(argv: Sequence[str]) -> None:
    # 不接受多余的位置参数。
    if len(argv) > 1:
        raise app.UsageError("Too many command-line arguments.")
    solve_pell(_COEFF.value, _MAX_VALUE.value)


if __name__ == "__main__":
    app.run(main)
