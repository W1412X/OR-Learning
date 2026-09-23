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

"""使用无等待作业车间调度为面包店安排烹饪任务。

我们调度一整天的烘焙生产：
  - 凌晨 4 点开工。
  - 商店晚上 10 点关门。
  - 时长以分钟计。时间从午夜开始计算。
"""

import collections
from typing import List, Sequence, Tuple

from absl import app
from absl import flags

from ortools.sat.python import cp_model

# flag：SAT 求解器参数（文本格式），默认 16 个搜索工作线程、30 秒时限
_PARAMS = flags.DEFINE_string(
    "params",
    "num_search_workers:16, max_time_in_seconds:30",
    "Sat solver parameters.",
)

# 食谱名称
CROISSANT = "croissant"
APPLE_PIE = "apple pie"
BRIOCHE = "brioche"
CHOCOLATE_CAKE = "chocolate cake"

# 技能名称（同时用作工序名）
BAKING = "baking"
PROOFING = "proofing"
COOKING = "cooking"
COOLING = "cooling"
DECORATING = "decorating"
DISPLAY = "display"


class Task:
    """单个烘焙任务。

    - 简单烘焙任务的时长固定，由工人完成。
    - 等待/冷却/发酵任务有最小与最大时长，
      由机器完成或占用空间类资源。
    """

    def __init__(self, name, min_duration, max_duration):
        self.name = name
        self.min_duration = min_duration
        self.max_duration = max_duration


class Skill:
    """工人的技能或机器的能力。"""

    def __init__(self, name, efficiency):
        self.name = name
        # 效率目前未被使用。
        self.efficiency = efficiency


class Recipe:
    """食谱是一串有序的烹饪任务。"""

    def __init__(self, name):
        self.name = name
        self.tasks = []

    def add_task(
        self, resource_name: str, min_duration: int, max_duration: int
    ) -> "Recipe":
        # 追加一道工序（技能名 + 最小/最大时长），支持链式调用
        self.tasks.append(Task(resource_name, min_duration, max_duration))
        return self


class Resource:
    """资源可以是工人、机器，或只是蛋糕放置的空间。

    - 工人容量为 1，可以有可变的效率。
    - 机器和空间的容量大于等于 1，但效率固定为 100。

      对效率为 k 的工人和时长为 t 的任务，实际工作时长为 `ceil(t * k)`。
    """

    def __init__(self, name, capacity):
        self.name = name
        self.capacity = capacity
        self.skills = []

    def add_skill(self, skill_name: str, efficiency: float) -> "Resource":
        # 为资源添加一项技能（技能名 + 效率），支持链式调用
        self.skills.append(Skill(skill_name, efficiency))
        return self


class Order:
    """订单是需要在给定交期前交付的食谱。"""

    def __init__(self, unique_id, recipe_name, due_date, quantity):
        """构建订单。

        Args:
          unique_id: 订单的唯一标识符，用于展示结果。
          recipe_name: 食谱名称，必须与某个食谱匹配。
          due_date: 交期（午夜后的分钟数）。
          quantity: 需要准备的蛋糕数量。
        """
        self.unique_id = unique_id
        self.recipe_name = recipe_name
        self.due_date = due_date
        self.quantity = quantity


def set_up_data() -> Tuple[List[Recipe], List[Resource], List[Order]]:
    """构建面包店问题的数据。"""

    # 食谱。
    # 可颂：烘焙(15) -> 发酵(60~90) -> 烹饪(20) -> 展示(5~300)
    croissant_recipe = Recipe(CROISSANT)
    croissant_recipe.add_task(BAKING, 15, 15)
    croissant_recipe.add_task(PROOFING, 60, 90)
    croissant_recipe.add_task(COOKING, 20, 20)
    croissant_recipe.add_task(DISPLAY, 5, 5 * 60)

    # 苹果派：烘焙(25) -> 发酵(15~60) -> 烹饪(30) -> 装饰(5) -> 展示(5~300)
    apple_pie_recipe = Recipe(APPLE_PIE)
    apple_pie_recipe.add_task(BAKING, 25, 25)
    apple_pie_recipe.add_task(PROOFING, 15, 60)
    apple_pie_recipe.add_task(COOKING, 30, 30)
    apple_pie_recipe.add_task(DECORATING, 5, 5)
    apple_pie_recipe.add_task(DISPLAY, 5, 5 * 60)

    # 奶油面包卷：烘焙(20) -> 发酵(60~90) -> 烹饪(30) -> 展示(5~300)
    brioche_recipe = Recipe(BRIOCHE)
    brioche_recipe.add_task(BAKING, 20, 20)
    brioche_recipe.add_task(PROOFING, 60, 90)
    brioche_recipe.add_task(COOKING, 30, 30)
    brioche_recipe.add_task(DISPLAY, 5, 5 * 60)

    # 巧克力蛋糕：烘焙(15) -> 烹饪(25) -> 装饰(15) -> 展示(5~300)
    chocolate_cake_recipe = Recipe(CHOCOLATE_CAKE)
    chocolate_cake_recipe.add_task(BAKING, 15, 15)
    chocolate_cake_recipe.add_task(COOKING, 25, 25)
    chocolate_cake_recipe.add_task(DECORATING, 15, 15)
    chocolate_cake_recipe.add_task(DISPLAY, 5, 5 * 60)
    recipes = [
        croissant_recipe,
        apple_pie_recipe,
        brioche_recipe,
        chocolate_cake_recipe,
    ]

    # 资源。
    # 工人容量为 1；机器/空间容量 >= 1
    baker1 = Resource("baker1", 1).add_skill(BAKING, 1.0)
    baker2 = Resource("baker2", 1).add_skill(BAKING, 1.0)
    decorator1 = Resource("decorator1", 1).add_skill(DECORATING, 1.0)
    waiting_space = Resource("waiting_space", 4).add_skill(PROOFING, 1.0)
    oven = Resource("oven", 4).add_skill(COOKING, 1.0)
    display_space = Resource("display_space", 12).add_skill(DISPLAY, 1.0)
    resources = [baker1, baker2, decorator1, waiting_space, oven, display_space]

    # 订单。
    # (唯一ID, 食谱, 交期(分钟), 数量)
    croissant_7am = Order("croissant_7am", CROISSANT, 7 * 60, 3)
    croissant_8am = Order("croissant_8am", CROISSANT, 8 * 60, 3)
    croissant_9am = Order("croissant_9am", CROISSANT, 9 * 60, 2)
    croissant_10am = Order("croissant_10am", CROISSANT, 10 * 60, 1)
    croissant_11am = Order("croissant_11am", CROISSANT, 11 * 60, 1)
    brioche_10am = Order("brioche_10am", BRIOCHE, 10 * 60, 8)
    brioche_12pm = Order("brioche_12pm", BRIOCHE, 12 * 60, 8)
    apple_pie_1pm = Order("apple_pie_1pm", APPLE_PIE, 13 * 60, 10)
    chocolate_4pm = Order("chocolate_4pm", CHOCOLATE_CAKE, 16 * 60, 10)
    orders = [
        croissant_7am,
        croissant_8am,
        croissant_9am,
        croissant_10am,
        croissant_11am,
        brioche_10am,
        brioche_12pm,
        apple_pie_1pm,
        chocolate_4pm,
    ]

    return recipes, resources, orders


def solve_with_cp_sat(
    recipes: List[Recipe], resources: List[Resource], orders: List[Order]
) -> None:
    """构建优化模型并求解问题。"""

    model = cp_model.CpModel()
    # 一天的结束时间：晚上 10 点
    horizon = 22 * 60  # 10PM.
    # 工作开始时间：凌晨 4 点
    start_work = 4 * 60  # 4am.

    # 按名称索引食谱。
    recipe_by_name = {}
    for recipe in recipes:
        recipe_by_name[recipe.name] = recipe

    # 按名称索引资源，并建立"技能名 -> 拥有该技能的资源列表"映射。
    resource_by_name = {}
    resource_list_by_skill_name = collections.defaultdict(list)
    for resource in resources:
        resource_by_name[resource.name] = resource
        for skill in resource.skills:
            resource_list_by_skill_name[skill.name].append(resource)

    # 解析订单，并为每个任务在每个合格资源上创建一份可选副本。
    # interval_list_by_resource_name：资源名 -> 该资源的区间副本列表
    # orders_sequence_of_events：作业ID -> [(时间变量, 事件名), ...]（用于打印）
    interval_list_by_resource_name = collections.defaultdict(list)
    orders_sequence_of_events = collections.defaultdict(list)
    sorted_orders = []
    # 所有作业的逾期变量（目标函数用）
    tardiness_vars = []
    for order in orders:
        # 每个数量单位展开为一个独立批次（作业）
        for batch in range(order.quantity):
            order_id = f"{order.unique_id}_{batch}"
            sorted_orders.append(order_id)
            previous_end = None
            due_date = order.due_date
            recipe = recipe_by_name[order.recipe_name]
            for task in recipe.tasks:
                # 工序名即技能名
                skill_name = task.name
                # 变量名后缀：作业ID + 批次号 + 工序名
                suffix = f"_{order.unique_id}_batch{batch}_{skill_name}"

                if previous_end is None:
                    # 第一道工序：创建开始时间变量（无等待链的入口）
                    start = model.new_int_var(start_work, horizon, f"start{suffix}")
                    orders_sequence_of_events[order_id].append(
                        (start, f"start{suffix}")
                    )
                else:
                    # 无等待衔接：后一道工序的开始 = 上一道的结束（共享变量）
                    start = previous_end

                # 决策变量：工序时长，范围 [min_duration, max_duration]
                size = model.new_int_var(
                    task.min_duration, task.max_duration, f"size{suffix}"
                )
                if task == recipe.tasks[-1]:
                    # 最后一道工序：订单必须在交期之后结束，最好恰好等于交期。
                    # end = tardiness + due_date，tardiness 即逾期时间
                    tardiness = model.new_int_var(0, horizon - due_date, f"end{suffix}")
                    end = tardiness + due_date

                    # 把逾期变量保存起来供目标函数使用。
                    tardiness_vars.append(tardiness)
                else:
                    # 中间工序：结束时间为独立变量
                    end = model.new_int_var(start_work, horizon, f"end{suffix}")
                orders_sequence_of_events[order_id].append((end, f"end{suffix}"))
                previous_end = end

                # 按资源创建可选区间副本。
                # 每道工序为每个具备所需技能的资源创建一份区间
                presence_literals = []
                for resource in resource_list_by_skill_name[skill_name]:
                    # presence：该工序是否由该资源执行
                    presence = model.new_bool_var(f"presence{suffix}_{resource.name}")
                    # 可选区间：start/size/end 加上 presence 字面量
                    copy = model.new_optional_interval_var(
                        start, size, end, presence, f"interval{suffix}_{resource.name}"
                    )
                    interval_list_by_resource_name[resource.name].append(copy)
                    presence_literals.append(presence)

                # 约束：只有一份副本会被执行（恰好指派给一个资源）。
                model.add_exactly_one(presence_literals)

    # 创建资源能力约束。
    for resource in resources:
        # 该资源的所有区间副本
        intervals = interval_list_by_resource_name[resource.name]
        if resource.capacity == 1:
            # 容量为 1：互斥（同一时刻只能执行一个任务）
            model.add_no_overlap(intervals)
        else:
            # 容量 > 1：累积约束（并发占用不超过容量）
            model.add_cumulative(intervals, [1] * len(intervals), resource.capacity)

    # 目标：最小化每个作业的逾期时间之和。
    # 逾期时间 = 作业结束时间与交期之差。
    model.minimize(sum(tardiness_vars))

    # 求解模型。
    solver = cp_model.CpSolver()
    if _PARAMS.value:
        # 解析文本格式的求解器参数（来自 --params flag）
        solver.parameters.parse_text_format(_PARAMS.value)
    # 强制开启搜索日志
    solver.parameters.log_search_progress = True
    status = solver.solve(model)

    if status == cp_model.OPTIMAL or status == cp_model.FEASIBLE:
        # 按订单批次打印各事件（工序开始/结束）的时刻
        for order_id in sorted_orders:
            print(f"{order_id}:")
            for time_expr, event_id in orders_sequence_of_events[order_id]:
                time = solver.value(time_expr)
                print(f"  {event_id} at {time // 60}:{time % 60:02}")


def main(argv: Sequence[str]) -> None:
    if len(argv) > 1:
        raise app.UsageError("Too many command-line arguments.")

    # 组装数据并求解
    recipes, resources, orders = set_up_data()
    solve_with_cp_sat(recipes, resources, orders)


if __name__ == "__main__":
    app.run(main)
