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

"""这是由 Lewis Carroll 发明的斑马问题。

有五栋房子。
英国人住在红房子里。
西班牙人养狗。
绿房子里喝咖啡。
乌克兰人喝茶。
绿房子紧挨在象牙色房子的右边。
抽 Old Gold 香烟的人养蜗牛。
黄房子里抽 Kools 香烟。
中间的房子喝牛奶。
挪威人住在第一栋房子。
抽 Chesterfields 香烟的人住在养狐狸的人隔壁。
抽 Kools 香烟的房子隔壁是养马的房子。
抽 Lucky Strike 香烟的人喝橙汁。
日本人抽 Parliaments 香烟。
挪威人住在蓝房子隔壁。

谁养斑马？谁喝水？
"""

from ortools.sat.python import cp_model


# pylint: disable=too-many-statements
def solve_zebra():
    """求解斑马问题。"""

    # 创建模型。
    model = cp_model.CpModel()

    # 颜色类别：变量取值代表该颜色房子所在的位置（1~5）
    red = model.new_int_var(1, 5, "red")
    green = model.new_int_var(1, 5, "green")
    yellow = model.new_int_var(1, 5, "yellow")
    blue = model.new_int_var(1, 5, "blue")
    ivory = model.new_int_var(1, 5, "ivory")

    # 国籍类别：变量取值代表该国籍的人所住房子的位置
    englishman = model.new_int_var(1, 5, "englishman")
    spaniard = model.new_int_var(1, 5, "spaniard")
    japanese = model.new_int_var(1, 5, "japanese")
    ukrainian = model.new_int_var(1, 5, "ukrainian")
    norwegian = model.new_int_var(1, 5, "norwegian")

    # 宠物类别：变量取值代表该宠物所在房子的位置
    dog = model.new_int_var(1, 5, "dog")
    snails = model.new_int_var(1, 5, "snails")
    fox = model.new_int_var(1, 5, "fox")
    zebra = model.new_int_var(1, 5, "zebra")
    horse = model.new_int_var(1, 5, "horse")

    # 饮料类别：变量取值代表该饮料被饮用的房子位置
    tea = model.new_int_var(1, 5, "tea")
    coffee = model.new_int_var(1, 5, "coffee")
    water = model.new_int_var(1, 5, "water")
    milk = model.new_int_var(1, 5, "milk")
    fruit_juice = model.new_int_var(1, 5, "fruit juice")

    # 香烟类别：变量取值代表该品牌香烟被抽的房子位置
    old_gold = model.new_int_var(1, 5, "old gold")
    kools = model.new_int_var(1, 5, "kools")
    chesterfields = model.new_int_var(1, 5, "chesterfields")
    lucky_strike = model.new_int_var(1, 5, "lucky strike")
    parliaments = model.new_int_var(1, 5, "parliaments")

    # 互斥约束：每个类别内部的 5 个属性分别位于 5 栋不同的房子
    model.add_all_different(red, green, yellow, blue, ivory)
    model.add_all_different(englishman, spaniard, japanese, ukrainian, norwegian)
    model.add_all_different(dog, snails, fox, zebra, horse)
    model.add_all_different(tea, coffee, water, milk, fruit_juice)
    model.add_all_different(parliaments, kools, chesterfields, lucky_strike, old_gold)

    # 线索：英国人住在红房子里
    model.add(englishman == red)
    # 线索：西班牙人养狗
    model.add(spaniard == dog)
    # 线索：绿房子里喝咖啡
    model.add(coffee == green)
    # 线索：乌克兰人喝茶
    model.add(ukrainian == tea)
    # 线索：绿房子紧挨在象牙色房子的右边（位置编号大 1）
    model.add(green == ivory + 1)
    # 线索：抽 Old Gold 香烟的人养蜗牛
    model.add(old_gold == snails)
    # 线索：黄房子里抽 Kools 香烟
    model.add(kools == yellow)
    # 线索：中间的房子（3 号）喝牛奶
    model.add(milk == 3)
    # 线索：挪威人住在第一栋房子
    model.add(norwegian == 1)

    # 线索：抽 Chesterfields 的人与养狐狸的人是隔壁邻居（位置相差 1）
    diff_fox_chesterfields = model.new_int_var(-4, 4, "diff_fox_chesterfields")
    model.add(diff_fox_chesterfields == fox - chesterfields)
    model.add_abs_equality(1, diff_fox_chesterfields)

    # 线索：抽 Kools 的房子与养马的房子是隔壁邻居（位置相差 1）
    diff_horse_kools = model.new_int_var(-4, 4, "diff_horse_kools")
    model.add(diff_horse_kools == horse - kools)
    model.add_abs_equality(1, diff_horse_kools)

    # 线索：抽 Lucky Strike 的人喝橙汁
    model.add(lucky_strike == fruit_juice)
    # 线索：日本人抽 Parliaments 香烟
    model.add(japanese == parliaments)

    # 线索：挪威人住在蓝房子隔壁（位置相差 1）
    diff_norwegian_blue = model.new_int_var(-4, 4, "diff_norwegian_blue")
    model.add(diff_norwegian_blue == norwegian - blue)
    model.add_abs_equality(1, diff_norwegian_blue)

    # 求解并打印解。
    solver = cp_model.CpSolver()
    status = solver.solve(model)

    if status == cp_model.OPTIMAL:
        # 在 5 位房主中找到与 water / zebra 处于同一栋房子的人
        people = [englishman, spaniard, japanese, ukrainian, norwegian]
        water_drinker = [p for p in people if solver.value(p) == solver.value(water)][0]
        zebra_owner = [p for p in people if solver.value(p) == solver.value(zebra)][0]
        print("The", water_drinker.name, "drinks water.")
        print("The", zebra_owner.name, "owns the zebra.")
    else:
        print("No solutions to the zebra problem, this is unusual!")


solve_zebra()
