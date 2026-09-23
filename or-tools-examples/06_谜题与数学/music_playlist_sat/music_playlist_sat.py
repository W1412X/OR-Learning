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

"""创建一张均衡的音乐播放列表。

从歌曲列表中选择歌曲来构造播放列表。

每首歌有时长（秒）与音乐流派（如 Rock、Disco、Techno 等）。

播放列表总时长必须尽可能接近给定总时长。每首歌在列表中
最多出现一次。所有存在的流派必须至少出现一次。相邻两首歌
的流派必须不同。从一个流派切换到另一个流派有正的成本，
播放列表需要最小化整体成本。
"""

from collections.abc import Sequence

from absl import app
from ortools.sat.python import cp_model


def Solve():
    """求解音乐播放列表问题。"""

    # --------------------
    # 1. 数据
    # --------------------
    # 曲库：每项为 (歌名, 时长秒, 流派)
    tunes = [
        ("Song 01", 202, "Pop"),
        ("Song 02", 233, "Techno"),
        ("Song 03", 108, "Disco"),
        ("Song 04", 281, "Disco"),
        ("Song 05", 129, "Techno"),
        ("Song 06", 122, "Techno"),
        ("Song 07", 244, "Pop"),
        ("Song 08", 178, "Techno"),
        ("Song 09", 213, "Techno"),
        ("Song 10", 124, "Rock"),
        ("Song 11", 120, "Disco"),
        ("Song 12", 196, "Rock"),
        ("Song 13", 249, "Disco"),
        ("Song 14", 294, "Disco"),
        ("Song 15", 103, "Techno"),
        ("Song 16", 179, "Disco"),
        ("Song 17", 146, "Disco"),
        ("Song 18", 126, "Techno"),
        ("Song 19", 100, "Pop"),
        ("Song 20", 122, "Disco"),
        ("Song 21", 190, "Disco"),
        ("Song 22", 181, "Techno"),
        ("Song 23", 273, "Pop"),
        ("Song 24", 121, "Disco"),
        ("Song 25", 159, "Pop"),
        ("Song 26", 234, "Rock"),
        ("Song 27", 169, "Rock"),
        ("Song 28", 151, "Rock"),
        ("Song 29", 142, "Techno"),
        ("Song 30", 245, "Pop"),
        ("Song 31", 281, "Techno"),
        ("Song 32", 154, "Rock"),
        ("Song 33", 148, "Disco"),
        ("Song 34", 120, "Pop"),
        ("Song 35", 163, "Disco"),
        ("Song 36", 158, "Pop"),
        ("Song 37", 235, "Rock"),
        ("Song 38", 106, "Techno"),
        ("Song 39", 117, "Disco"),
        ("Song 40", 110, "Pop"),
        ("Song 41", 144, "Rock"),
        ("Song 42", 156, "Disco"),
        ("Song 43", 204, "Rock"),
        ("Song 44", 108, "Pop"),
        ("Song 45", 255, "Pop"),
        ("Song 46", 165, "Rock"),
        ("Song 47", 290, "Disco"),
        ("Song 48", 242, "Pop"),
        ("Song 49", 272, "Rock"),
        ("Song 50", 212, "Pop"),
    ]

    # 流派转换成本。成本越高表示越不希望发生这种衔接。
    genre_transition_costs = {
        "Rock": {"Pop": 3, "Disco": 5, "Techno": 7},
        "Pop": {"Rock": 3, "Disco": 6, "Techno": 8},
        "Disco": {"Rock": 5, "Pop": 6, "Techno": 9},
        "Techno": {"Rock": 7, "Pop": 8, "Disco": 9},
    }

    num_tunes = len(tunes)
    all_tunes = range(num_tunes)

    # 播放列表目标时长（秒）。
    target_duration = 60 * 60  # 1 小时

    # 我们使用回路约束来建模播放列表。在回路约束图中，
    # 每个节点是一首歌，每条弧表示播放列表中一对相邻的歌曲。
    # 我们引入一个哑节点来表示播放列表的开始与结束。
    #
    # "相邻两首歌流派必须不同"这一约束的编码方式是：
    # 根本不创建同流派歌曲之间的弧。这对本问题的建模至关重要：
    # 既减少了模型中的变量数量，又避免了为保证相邻流派不同
    # 而添加额外约束。

    # 表示播放列表开始与结束的哑节点。
    dummy_node = num_tunes

    # `possible_successors[i]` 包含节点 i 之后可以到达的节点列表。
    possible_successors = {}
    possible_successors[dummy_node] = [dummy_node]
    for i in all_tunes:
        # 任何节点都可以成为播放列表的第一首歌。
        possible_successors[dummy_node].append(i)
        # 任何节点都可以成为播放列表的最后一首歌。
        possible_successors[i] = [dummy_node]
        genre_i = tunes[i][2]
        for j in all_tunes:
            genre_j = tunes[j][2]
            # 若 i 与 j 流派不同，则可以从 i 走到 j。
            if genre_i != genre_j:
                possible_successors[i].append(j)

    # --------------------
    # 2. 模型
    # --------------------
    model = cp_model.CpModel()

    # --------------------
    # 3. 决策变量
    # --------------------
    # `literals[(i, j)]` 为真表示在播放列表中歌曲 j 紧跟在歌曲 i 之后。
    literals = {}

    # --------------------
    # 4. 约束
    # --------------------

    # 4.1 相邻两首歌流派必须不同。
    # 这已经编码在 possible_successors 中——同流派歌曲之间没有弧。
    # 现在只需添加回路约束即可。

    # `arcs` 包含回路图中所有可能的弧，
    # 每条弧是一个三元组 (i, j, literals[(i, j)])。
    arcs = []

    def AddArc(i, j):
        # 为弧 (i, j) 创建布尔决策变量并加入弧列表
        literals[(i, j)] = model.new_bool_var(f"lit_{i}_{j}")
        arcs.append((i, j, literals[(i, j)]))

    # 在不同节点之间添加所有可能的弧。
    for i, successors in possible_successors.items():
        for j in successors:
            AddArc(i, j)

    # 添加自弧，允许歌曲不在播放列表中。
    for i in all_tunes:
        AddArc(i, i)

    # 用这些弧添加回路约束。
    model.add_circuit(arcs)

    # 4.2 所有流派必须至少出现一次。
    # 编码方式：对每个流派，其所有歌曲的活跃文字之和至少为 1。

    # `is_active[i]` 为真当且仅当歌曲 i 在播放列表中，
    # 即它的自弧在回路中未被选中。
    is_active = {}
    for i in all_tunes:
        is_active[i] = literals[(i, i)].Not()

    # `genre_tunes[genre]` 包含流派为 genre 的歌曲列表。
    genre_tunes = {}
    for genre in genre_transition_costs:
        genre_tunes[genre] = []
    for i in all_tunes:
        genre_tunes[tunes[i][2]].append(i)

    # 对每个流派，至少一首歌必须活跃：该流派所有文字之和 >= 1。
    for t in genre_tunes.values():
        model.add(sum(is_active[i] for i in t) >= 1)

    # --------------------
    # 5. 目标函数
    # --------------------

    # 5.1. 最小化流派转换成本。

    # 添加 total_transition_cost 变量，表示播放列表中所有转换成本之和。
    max_transition_cost = 0
    for genre_costs in genre_transition_costs.values():
        for cost in genre_costs.values():
            max_transition_cost = max(cost, max_transition_cost)
    # 成本上界：(歌曲数-1) * 最大单次转换成本
    total_transition_cost_upper_bound = (num_tunes - 1) * max_transition_cost
    total_transition_cost = model.new_int_var(
        0, total_transition_cost_upper_bound, "total_transition_cost"
    )

    # 目标项：每条跨流派弧的成本 * 弧是否被选中
    transition_cost_terms = []
    for i, successors in possible_successors.items():
        if i == dummy_node:
            continue
        genre_i = tunes[i][2]
        for j in successors:
            if j == dummy_node:
                continue
            genre_j = tunes[j][2]
            cost = genre_transition_costs[genre_i][genre_j]
            transition_cost_terms.append(cost * literals[(i, j)])
    # 约束：总转换成本等于所有被选中弧的成本之和
    model.add(total_transition_cost == sum(transition_cost_terms))

    # 5.2. 最小化目标时长与实际总时长的偏差。

    # 添加 total_duration 变量，表示所有活跃歌曲的时长之和。
    total_duration_upper_bound = sum([t[1] for t in tunes])
    total_duration = model.new_int_var(0, total_duration_upper_bound, "total_duration")
    # 约束：总时长 = 每首歌时长 * 该歌是否被选
    model.add(total_duration == sum(tunes[i][1] * is_active[i] for i in all_tunes))

    # 最小化与目标时长的绝对差。
    # deviation 变量取 |总时长 - 目标时长|
    deviation = model.new_int_var(0, target_duration, "deviation")
    model.add_abs_equality(deviation, total_duration - target_duration)

    # 5.3. 合并两个目标。
    #
    # 可以加权重来决定两者的优先级。
    # 例如：`model.minimize(10 * total_transition_cost + deviation)`
    # 目标：转换成本 + 时长偏差之和最小化
    model.minimize(total_transition_cost + deviation)

    # --------------------
    # 6. 求解
    # --------------------
    solver = cp_model.CpSolver()
    # 为求解器设置时限（30 秒）
    solver.parameters.max_time_in_seconds = 30.0
    status = solver.solve(model)

    # -----------------------
    # 7. 打印解
    # -----------------------
    if status == cp_model.OPTIMAL:
        print("Found Optimal Playlist:")
    elif status == cp_model.FEASIBLE:
        print("Found Feasible Playlist:")
    else:
        print("No solution found.")
        return

    # 打印总转换成本
    print(f"  Total Transition Cost: {solver.value(total_transition_cost)}")
    print(
        f"  Playlist Duration: {solver.value(total_duration)} seconds "
        f"({solver.value(total_duration) / 60:.2f} minutes)"
    )
    print(
        f"  Deviation from target duration ({target_duration}):"
        f" {solver.value(deviation)} seconds"
    )
    print("-" * 30)

    # 从哑节点出发重建播放列表序列。
    playlist = []
    current_node = dummy_node
    while True:
        # 寻找当前节点的后继节点。
        next_node = dummy_node
        for next_node in possible_successors[current_node]:
            if solver.value(literals[(current_node, next_node)]):
                break

        if next_node == dummy_node:
            break  # 回到了起点，遍历完成。

        # 记录访问到的歌曲并继续前进
        playlist.append(next_node)
        current_node = next_node

    if not playlist:
        print("Empty playlist.")
    else:
        # 按顺序打印每首歌：序号、歌名、流派、时长
        for i in playlist:
            (name, duration, genre) = tunes[i]
            print(f"{i+1}. {name} ({genre}) - {duration}s")


def main(argv: Sequence[str]) -> None:
    if len(argv) > 1:
        raise app.UsageError("Too many command-line arguments.")
    Solve()


if __name__ == "__main__":
    app.run(main)
