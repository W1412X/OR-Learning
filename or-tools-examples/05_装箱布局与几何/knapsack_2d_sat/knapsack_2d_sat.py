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

"""求解二维矩形背包问题。

本代码改编自
https://yetanothermathprogrammingconsultant.blogspot.com/2021/10/2d-knapsack-problem.html
"""

import io

from absl import app
from absl import flags
import numpy as np
import pandas as pd

from ortools.sat.python import cp_model


# flag：把 CP-SAT 模型 proto 写入指定的输出文件。
_OUTPUT_PROTO = flags.DEFINE_string(
    "output_proto", "", "Output file to write the cp_model proto to."
)
# flag：SAT 求解器参数（文本格式）。
_PARAMS = flags.DEFINE_string(
    "params",
    "num_search_workers:16,log_search_progress:true,max_time_in_seconds:45",
    "Sat solver parameters.",
)
# flag：选择建模方式（duplicate / rotation / optional）。
_MODEL = flags.DEFINE_string(
    "model", "rotation", "'duplicate' or 'rotation' or 'optional'"
)


def build_data() -> tuple[pd.Series, int, int]:
    """构建数据表。"""
    # 内联物品数据：名称、宽、高、可用数量、价值、颜色。
    data = """
    item         width    height available    value    color
    k1             20       4       2        338.984   blue
    k2             12      17       6        849.246   orange
    k3             20      12       2        524.022   green
    k4             16       7       9        263.303   red
    k5              3       6       3        113.436   purple
    k6             13       5       3        551.072   brown
    k7              4       7       6         86.166   pink
    k8              6      18       8        755.094   grey
    k9             14       2       7        223.516   olive
    k10             9      11       5        369.560   cyan
    """

    data = pd.read_table(io.StringIO(data), sep=r"\s+")
    print("Input data")
    print(data)

    # 容器的最大高度与最大宽度。
    max_height = 20
    max_width = 30

    print(f"Container max_width:{max_width} max_height:{max_height}")
    print(f"#Items: {len(data.index)}")
    return (data, max_height, max_width)


def solve_with_duplicate_items(
    data: pd.Series, max_height: int, max_width: int
) -> None:
    """通过为每个物品构建 2 个副本（旋转版与未旋转版）来求解问题。"""
    # 展开后的数据（按 available 数量复制成单个物品）。
    data_widths = data["width"].to_numpy()
    data_heights = data["height"].to_numpy()
    data_availability = data["available"].to_numpy()
    data_values = data["value"].to_numpy()

    # 未复制（原始）物品的数据：按可用数量展开。
    base_item_widths = np.repeat(data_widths, data_availability)
    base_item_heights = np.repeat(data_heights, data_availability)
    base_item_values = np.repeat(data_values, data_availability)
    num_data_items = len(base_item_values)

    # 通过复制创建旋转物品：宽高互换。
    item_widths = np.concatenate((base_item_widths, base_item_heights))
    item_heights = np.concatenate((base_item_heights, base_item_widths))
    item_values = np.concatenate((base_item_values, base_item_values))

    num_items = len(item_values)

    # OR-Tools 模型
    model = cp_model.CpModel()

    # 变量
    x_starts = []
    x_ends = []
    y_starts = []
    y_ends = []
    is_used = []
    x_intervals = []
    y_intervals = []

    for i in range(num_items):
        ## 物品是否被使用？
        is_used.append(model.new_bool_var(f"is_used{i}"))

        ## 物品坐标变量（x/y 的起点与终点）。
        x_starts.append(model.new_int_var(0, max_width, f"x_start{i}"))
        x_ends.append(model.new_int_var(0, max_width, f"x_end{i}"))
        y_starts.append(model.new_int_var(0, max_height, f"y_start{i}"))
        y_ends.append(model.new_int_var(0, max_height, f"y_end{i}"))

        ## 区间变量：长度为 物品尺寸 * is_used，未选用时长度为 0。
        x_intervals.append(
            model.new_interval_var(
                x_starts[i],
                item_widths[i] * is_used[i],
                x_ends[i],
                f"x_interval{i}",
            )
        )
        y_intervals.append(
            model.new_interval_var(
                y_starts[i],
                item_heights[i] * is_used[i],
                y_ends[i],
                f"y_interval{i}",
            )
        )

        # 未使用的盒子固定在原点 (0, 0)。
        model.add(x_starts[i] == 0).only_enforce_if(~is_used[i])
        model.add(y_starts[i] == 0).only_enforce_if(~is_used[i])

    # 约束。

    ## 同一物品的"未旋转版"与"旋转版"副本至多只能使用一个。
    for i in range(num_data_items):
        model.add(is_used[i] + is_used[i + num_data_items] <= 1)

    ## 二维互不重叠约束。
    model.add_no_overlap_2d(x_intervals, y_intervals)

    ## 目标函数：最大化所选物品的总价值。
    model.maximize(cp_model.LinearExpr.weighted_sum(is_used, item_values))

    # 按需把模型 proto 写入文件。
    if _OUTPUT_PROTO.value:
        print(f"Writing proto to {_OUTPUT_PROTO.value}")
        with open(_OUTPUT_PROTO.value, "w") as text_file:
            text_file.write(str(model))

    # 求解模型。
    solver = cp_model.CpSolver()
    if _PARAMS.value:
        solver.parameters.parse_text_format(_PARAMS.value)

    status = solver.solve(model)

    # 报告解。
    if status in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        # 收集被选中的物品索引。
        used = {i for i in range(num_items) if solver.boolean_value(is_used[i])}
        data = pd.DataFrame(
            {
                "x_start": [solver.value(x_starts[i]) for i in used],
                "y_start": [solver.value(y_starts[i]) for i in used],
                "item_width": [item_widths[i] for i in used],
                "item_height": [item_heights[i] for i in used],
                "x_end": [solver.value(x_ends[i]) for i in used],
                "y_end": [solver.value(y_ends[i]) for i in used],
                "item_value": [item_values[i] for i in used],
            }
        )
        print(data)


def solve_with_duplicate_optional_items(
    data: pd.Series, max_height: int, max_width: int
):
    """通过为每个物品构建 2 个可选副本（旋转版与未旋转版）来求解问题。"""
    # 展开后的数据（按 available 数量复制成单个物品）。
    data_widths = data["width"].to_numpy()
    data_heights = data["height"].to_numpy()
    data_availability = data["available"].to_numpy()
    data_values = data["value"].to_numpy()

    # 未复制（原始）物品的数据：按可用数量展开。
    base_item_widths = np.repeat(data_widths, data_availability)
    base_item_heights = np.repeat(data_heights, data_availability)
    base_item_values = np.repeat(data_values, data_availability)
    num_data_items = len(base_item_values)

    # 通过复制创建旋转物品：宽高互换。
    item_widths = np.concatenate((base_item_widths, base_item_heights))
    item_heights = np.concatenate((base_item_heights, base_item_widths))
    item_values = np.concatenate((base_item_values, base_item_values))

    num_items = len(item_values)

    # OR-Tools 模型
    model = cp_model.CpModel()

    # 变量
    x_starts = []
    y_starts = []
    is_used = []
    x_intervals = []
    y_intervals = []

    for i in range(num_items):
        ## 物品是否被使用？
        is_used.append(model.new_bool_var(f"is_used{i}"))

        ## 物品坐标变量：起点范围按物品尺寸收紧，天然保证不越出容器边界。
        x_starts.append(
            model.new_int_var(0, max_width - int(item_widths[i]), f"x_start{i}")
        )
        y_starts.append(
            model.new_int_var(0, max_height - int(item_heights[i]), f"y_start{i}")
        )

        ## 可选定长区间变量：仅当 is_used[i] 为真时区间才"存在"。
        x_intervals.append(
            model.new_optional_fixed_size_interval_var(
                x_starts[i], item_widths[i], is_used[i], f"x_interval{i}"
            )
        )
        y_intervals.append(
            model.new_optional_fixed_size_interval_var(
                y_starts[i], item_heights[i], is_used[i], f"y_interval{i}"
            )
        )
        # 未使用的盒子固定在原点 (0, 0)。
        model.add(x_starts[i] == 0).only_enforce_if(~is_used[i])
        model.add(y_starts[i] == 0).only_enforce_if(~is_used[i])

    # 约束。

    ## 同一物品的"未旋转版"与"旋转版"副本至多只能使用一个。
    for i in range(num_data_items):
        model.add(is_used[i] + is_used[i + num_data_items] <= 1)

    ## 二维互不重叠约束。
    model.add_no_overlap_2d(x_intervals, y_intervals)

    ## 目标函数：最大化所选物品的总价值。
    model.maximize(cp_model.LinearExpr.weighted_sum(is_used, item_values))

    # 按需把模型 proto 写入文件。
    if _OUTPUT_PROTO.value:
        print(f"Writing proto to {_OUTPUT_PROTO.value}")
        with open(_OUTPUT_PROTO.value, "w") as text_file:
            text_file.write(str(model))

    # 求解模型。
    solver = cp_model.CpSolver()
    if _PARAMS.value:
        solver.parameters.parse_text_format(_PARAMS.value)

    status = solver.solve(model)

    # 报告解。
    if status in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        # 收集被选中的物品索引。
        used = {i for i in range(num_items) if solver.boolean_value(is_used[i])}
        data = pd.DataFrame(
            {
                "x_start": [solver.value(x_starts[i]) for i in used],
                "y_start": [solver.value(y_starts[i]) for i in used],
                "item_width": [item_widths[i] for i in used],
                "item_height": [item_heights[i] for i in used],
                "x_end": [solver.value(x_starts[i]) + item_widths[i] for i in used],
                "y_end": [solver.value(y_starts[i]) + item_heights[i] for i in used],
                "item_value": [item_values[i] for i in used],
            }
        )
        print(data)


def solve_with_rotations(data: pd.Series, max_height: int, max_width: int):
    """通过旋转物品来求解问题。"""
    # 展开后的数据（按 available 数量复制成单个物品）。
    data_widths = data["width"].to_numpy()
    data_heights = data["height"].to_numpy()
    data_availability = data["available"].to_numpy()
    data_values = data["value"].to_numpy()

    item_widths = np.repeat(data_widths, data_availability)
    item_heights = np.repeat(data_heights, data_availability)
    item_values = np.repeat(data_values, data_availability)

    num_items = len(item_widths)

    # OR-Tools 模型。
    model = cp_model.CpModel()

    # 每个矩形的坐标变量。
    x_starts = []
    x_sizes = []
    x_ends = []
    y_starts = []
    y_sizes = []
    y_ends = []
    x_intervals = []
    y_intervals = []

    for i in range(num_items):
        # 尺寸变量的候选取值：{0, 宽, 高}（0 表示未选用）。
        sizes = [0, int(item_widths[i]), int(item_heights[i])]
        # X 坐标变量。
        x_starts.append(model.new_int_var(0, max_width, f"x_start{i}"))
        x_sizes.append(
            model.new_int_var_from_domain(
                cp_model.Domain.FromValues(sizes), f"x_size{i}"
            )
        )
        x_ends.append(model.new_int_var(0, max_width, f"x_end{i}"))

        # Y 坐标变量。
        y_starts.append(model.new_int_var(0, max_height, f"y_start{i}"))
        y_sizes.append(
            model.new_int_var_from_domain(
                cp_model.Domain.FromValues(sizes), f"y_size{i}"
            )
        )
        y_ends.append(model.new_int_var(0, max_height, f"y_end{i}"))

        ## 区间变量：把 x/y 两个维度的起点、尺寸、终点绑定在一起。
        x_intervals.append(
            model.new_interval_var(x_starts[i], x_sizes[i], x_ends[i], f"x_interval{i}")
        )
        y_intervals.append(
            model.new_interval_var(y_starts[i], y_sizes[i], y_ends[i], f"y_interval{i}")
        )

    # is_used[i] == True 当且仅当物品 i 被选中。
    is_used = []

    # 约束。

    ## 对每个物品，决定其状态：未选（not_selected）、不旋转（no_rotation）、旋转（rotated）。
    for i in range(num_items):
        not_selected = model.new_bool_var(f"not_selected_{i}")
        no_rotation = model.new_bool_var(f"no_rotation_{i}")
        rotated = model.new_bool_var(f"rotated_{i}")

        ### 三种状态必须恰好选择其一。
        model.add_exactly_one(not_selected, no_rotation, rotated)

        ### 根据状态定义物品的宽与高。
        dim1 = item_widths[i]
        dim2 = item_heights[i]
        # 未使用的盒子固定在原点 (0, 0)，宽高为 0。
        model.add(x_sizes[i] == 0).only_enforce_if(not_selected)
        model.add(y_sizes[i] == 0).only_enforce_if(not_selected)
        model.add(x_starts[i] == 0).only_enforce_if(not_selected)
        model.add(y_starts[i] == 0).only_enforce_if(not_selected)
        # 不旋转时宽高为原始尺寸。
        model.add(x_sizes[i] == dim1).only_enforce_if(no_rotation)
        model.add(y_sizes[i] == dim2).only_enforce_if(no_rotation)
        # 旋转 90 度时宽高互换。
        model.add(x_sizes[i] == dim2).only_enforce_if(rotated)
        model.add(y_sizes[i] == dim1).only_enforce_if(rotated)

        # is_used 即"未选状态"的否定。
        is_used.append(~not_selected)

    ## 二维互不重叠约束。
    model.add_no_overlap_2d(x_intervals, y_intervals)

    # 目标函数：最大化所选物品的总价值。
    model.maximize(cp_model.LinearExpr.weighted_sum(is_used, item_values))

    # 按需把模型 proto 写入文件。
    if _OUTPUT_PROTO.value:
        print(f"Writing proto to {_OUTPUT_PROTO.value}")
        with open(_OUTPUT_PROTO.value, "w") as text_file:
            text_file.write(str(model))

    # 求解模型。
    solver = cp_model.CpSolver()
    if _PARAMS.value:
        solver.parameters.parse_text_format(_PARAMS.value)

    status = solver.solve(model)

    # 报告解。
    if status in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        # 收集被选中的物品索引。
        used = {i for i in range(num_items) if solver.boolean_value(is_used[i])}
        data = pd.DataFrame(
            {
                "x_start": [solver.value(x_starts[i]) for i in used],
                "y_start": [solver.value(y_starts[i]) for i in used],
                "item_width": [solver.value(x_sizes[i]) for i in used],
                "item_height": [solver.value(y_sizes[i]) for i in used],
                "x_end": [solver.value(x_ends[i]) for i in used],
                "y_end": [solver.value(y_ends[i]) for i in used],
                "item_value": [item_values[i] for i in used],
            }
        )
        print(data)


def main(_):
    """按所选建模方式求解问题。"""
    data, max_height, max_width = build_data()
    if _MODEL.value == "duplicate":
        solve_with_duplicate_items(data, max_height, max_width)
    elif _MODEL.value == "optional":
        solve_with_duplicate_optional_items(data, max_height, max_width)
    else:
        # 默认（rotation）使用旋转状态法建模。
        solve_with_rotations(data, max_height, max_width)


if __name__ == "__main__":
    app.run(main)
