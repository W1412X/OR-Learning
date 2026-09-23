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

"""按顺序收集宝箱并逃出迷宫。

路径必须从 'start' 位置出发，在 'end' 位置结束，
按顺序访问所有宝箱，并且在 4x4x4 地图上每个方块恰好走过一次。

合法移动为 6 个方向之一的一步：
  x+, x-, y+, y-, z+(向上), z-(向下)
"""

from typing import Dict, Sequence, Tuple

from absl import app
from absl import flags

from ortools.sat.python import cp_model

# flag：输出文件路径，非空时把 cp_model proto 写入该文件
_OUTPUT_PROTO = flags.DEFINE_string(
    "output_proto", "", "Output file to write the cp_model proto to."
)
# flag：SAT 求解器参数（文本格式），默认 8 个搜索工作线程并开启搜索日志
_PARAMS = flags.DEFINE_string(
    "params",
    "num_search_workers:8,log_search_progress:true",
    "Sat solver parameters.",
)


def add_neighbor(
    size: int,
    x: int,
    y: int,
    z: int,
    dx: int,
    dy: int,
    dz: int,
    model: cp_model.CpModel,
    index_map: Dict[Tuple[int, int, int], int],
    position_to_rank: Dict[Tuple[int, int, int], cp_model.IntVar],
    arcs: list[Tuple[int, int, cp_model.LiteralT]],
) -> None:
    """检查邻居是否合法，若合法则把对应弧加入模型。"""
    # 邻居坐标越界则不添加这条弧
    if (
        x + dx < 0
        or x + dx >= size
        or y + dy < 0
        or y + dy >= size
        or z + dz < 0
        or z + dz >= size
    ):
        return
    # 当前格子的节点索引与排名变量
    before_index = index_map[(x, y, z)]
    before_rank = position_to_rank[(x, y, z)]
    # 邻居格子的节点索引与排名变量
    after_index = index_map[(x + dx, y + dy, z + dz)]
    after_rank = position_to_rank[(x + dx, y + dy, z + dz)]
    # 新建布尔变量表示"是否走这条弧"
    move_literal = model.new_bool_var("")
    # 条件约束：走这条弧时，邻居的排名必须比当前格子大 1（保证路径连续）
    model.add(after_rank == before_rank + 1).only_enforce_if(move_literal)
    # 把 (尾节点, 头节点, 字面量) 三元组加入弧列表
    arcs.append((before_index, after_index, move_literal))


def escape_the_maze(params: str, output_proto: str) -> None:
    """逃出迷宫。"""
    # 网格边长：4x4x4
    size = 4
    # 4 个宝箱坐标（必须按列表顺序依次访问）
    boxes = [(0, 1, 0), (2, 0, 1), (1, 3, 1), (3, 1, 3)]
    # 起点与终点
    start = (3, 3, 0)
    end = (1, 0, 0)

    # 为网格中每个位置建立与唯一整数 0..size^3-1 的映射，
    # 供 circuit 约束的节点索引用。
    index_map = {}
    reverse_map = []
    counter = 0
    for x in range(size):
        for y in range(size):
            for z in range(size):
                index_map[(x, y, z)] = counter
                reverse_map.append((x, y, z))
                counter += 1

    # 开始构建模型。
    model = cp_model.CpModel()
    # 排名变量字典：coord -> IntVar
    position_to_rank = {}

    for coord in reverse_map:
        # 决策变量：每个格子的访问次序排名，取值 0..counter-1
        position_to_rank[coord] = model.new_int_var(0, counter - 1, f"rank_{coord}")

    # 路径顺序约束。
    # 起点排名为 0
    model.add(position_to_rank[start] == 0)
    # 终点排名为最大值（最后一个被访问）
    model.add(position_to_rank[end] == counter - 1)
    # 宝箱必须按给定顺序被访问（排名严格递增）
    for i in range(len(boxes) - 1):
        model.add(position_to_rank[boxes[i]] < position_to_rank[boxes[i + 1]])

    # 回路约束：所有方块恰好访问一次，并维护每个方块的排名。
    arcs: list[Tuple[int, int, cp_model.LiteralT]] = []
    for x in range(size):
        for y in range(size):
            for z in range(size):
                # 对每个格子枚举 6 个方向（x-、x+、y-、y+、z-、z+）的邻居
                add_neighbor(
                    size, x, y, z, -1, 0, 0, model, index_map, position_to_rank, arcs
                )
                add_neighbor(
                    size, x, y, z, 1, 0, 0, model, index_map, position_to_rank, arcs
                )
                add_neighbor(
                    size, x, y, z, 0, -1, 0, model, index_map, position_to_rank, arcs
                )
                add_neighbor(
                    size, x, y, z, 0, 1, 0, model, index_map, position_to_rank, arcs
                )
                add_neighbor(
                    size, x, y, z, 0, 0, -1, model, index_map, position_to_rank, arcs
                )
                add_neighbor(
                    size, x, y, z, 0, 0, 1, model, index_map, position_to_rank, arcs
                )

    # 把回路闭合：约束要求的是回路（circuit）而不是路径（path），
    # 因此添加一条从终点直接回到起点、恒为真的弧。
    arcs.append((index_map[end], index_map[start], True))

    # 添加回路（哈密顿路径）约束。
    model.add_circuit(arcs)

    # 如有需要则导出模型。
    if output_proto:
        model.export_to_file(output_proto)

    # 求解模型。
    solver = cp_model.CpSolver()
    if params:
        # 解析文本格式的求解器参数
        solver.parameters.parse_text_format(params)
    # 强制开启搜索日志
    solver.parameters.log_search_progress = True
    result = solver.solve(model)

    # 打印解。
    if result == cp_model.OPTIMAL:
        # path[rank] 为排名为 rank 的格子的描述字符串
        path = [""] * counter
        for x in range(size):
            for y in range(size):
                for z in range(size):
                    position = (x, y, z)
                    # 读取该格子解中的排名
                    rank = solver.value(position_to_rank[position])
                    msg = f"({x}, {y}, {z})"
                    # 标注起点、终点或宝箱
                    if position == start:
                        msg += " [start]"
                    elif position == end:
                        msg += " [end]"
                    else:
                        for b, box in enumerate(boxes):
                            if position == box:
                                msg += f" [boxes {b}]"
                    path[rank] = msg
        # 按访问顺序打印完整路径
        print(path)


def main(argv: Sequence[str]) -> None:
    if len(argv) > 1:
        raise app.UsageError("Too many command-line arguments.")
    escape_the_maze(_PARAMS.value, _OUTPUT_PROTO.value)


if __name__ == "__main__":
    app.run(main)
