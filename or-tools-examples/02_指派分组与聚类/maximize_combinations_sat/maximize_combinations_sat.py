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

"""最大化布尔变量的有效组合数量。"""

from typing import Sequence

from absl import app

from ortools.sat.python import cp_model


def maximize_combinations_sat() -> None:
    """最大化布尔变量的有效组合数量。"""
    # 创建 CP-SAT 模型
    model = cp_model.CpModel()
    # 决策变量：4 张卡是否被选中（布尔变量）
    cards: list[cp_model.IntVar] = [
        model.new_bool_var("card1"),
        model.new_bool_var("card2"),
        model.new_bool_var("card3"),
        model.new_bool_var("card4"),
    ]

    # 预定义的 4 个有价值组合：组合内所有卡都被选中时该组合才有效
    combos: list[list[cp_model.IntVar]] = [
        [cards[0], cards[1]],
        [cards[0], cards[2]],
        [cards[1], cards[3]],
        [cards[0], cards[2], cards[3]],
    ]

    # 牌库大小：恰好选中 3 张卡
    deck_size: int = 3
    # 约束：选中的卡数等于 deck_size
    model.add(sum(cards) == deck_size)

    # 为每个组合创建"有效性"布尔变量，并与组合内的卡双向链接
    valid_combos: list[cp_model.IntVar] = []
    for combination in combos:
        # is_valid 为真表示该组合内的所有卡都被选中
        is_valid = model.new_bool_var("")

        # 组合内全部为真 蕴含 is_valid。
        # （当前提 combination 全为真时，强制 is_valid 为真）
        model.add_bool_and(is_valid).only_enforce_if(combination)

        # is_valid 蕴含组合内全部为真。
        # （对组合中的每张卡分别添加蕴含 is_valid -> 卡为真）
        for literal in combination:
            model.add_implication(is_valid, literal)
        valid_combos.append(is_valid)

    # 目标函数：最大化有效组合的数量
    model.maximize(sum(valid_combos))

    # 创建 CP-SAT 求解器并开启搜索日志
    solver = cp_model.CpSolver()
    solver.parameters.log_search_progress = True
    # 求解模型
    status = solver.solve(model)

    if status == cp_model.OPTIMAL:
        # 达到最优时打印所有被选中的卡
        print(
            "chosen cards:",
            [card.name for card in cards if solver.boolean_value(card)],
        )


def main(argv: Sequence[str]) -> None:
    if len(argv) > 1:
        raise app.UsageError("Too many command-line arguments.")
    maximize_combinations_sat()


if __name__ == "__main__":
    app.run(main)
