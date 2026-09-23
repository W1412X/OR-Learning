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

"""马术场地障碍赛（Horse Jumping Show）排期问题。

一场为期三天的马术场地障碍赛将于明年冬天在日内瓦举行。赛事汇聚了来自
世界各地的骑手和马匹，期间举行多项不同的比赛。赛前六个月，骑手们向组织
方提交参赛报名（即骑手姓名、马匹、比赛）。骑手可以提交多个报名，例如带
多匹马参加同一场比赛，或参加多场比赛。

场地空间还存在额外限制。例如，场馆有 100 个马厩、4 个赛场（可安排比赛）
和 6 个热身场（骑手上场前热身用）。理想情况下，热身场最好不要被多个比赛
的骑手同时挤占。

组织方的目标是找到一份赛程表：各场比赛互不重叠，且它们的举办时间分散在
全天各处（并希望不要安排得太早）。比赛的开始时间只能是整点或半点（如
9:30、10:00、10:30 等）。比赛只能安排在有日光的时段进行，唯一例外是在
Main Stage 场地举行的比赛——该场地带顶棚并有照明设备。此外，初学者比赛
（1.10m 及以下）安排在第一天，高级比赛（1.50m 及以上）安排在最后一天。

明年冬天赛事的信息如下：
可用马厩：100
骑手数量：100
马匹数量：130
报名数量：200
比赛数量：15

场地：
- Main Stage 赛场：带顶棚（9AM-11PM）
- Highlands 赛场：仅日光时段（9AM-5PM）
- Sawdust 赛场：仅日光时段（9AM-5PM）
- 热身场 1：可容纳 10 名骑手，服务 Main Stage
- 热身场 2：可容纳 6 名骑手，服务 Main Stage
- 热身场 3：可容纳 8 名骑手，服务 Main Stage、Highlands
- 热身场 4：可容纳 8 名骑手，服务 Highlands、Sawdust
- 热身场 5：可容纳 9 名骑手，服务 Sawdust
- 热身场 6：可容纳 7 名骑手，服务 Sawdust

比赛：
- C_5_1.10m_Year_Olds  1.10m -  60 分钟
- C_6_1.25m_Year_Olds  1.25m -  90 分钟
- C_7_1.35m_Year_Olds  1.35m - 120 分钟
- C_0.8m_Jumpers       0.80m - 240 分钟
- C_1.0m_Jumpers       1.00m - 180 分钟
- C_1.10m_Jumpers      1.10m - 180 分钟
- C_1.20m_Jumpers      1.20m - 120 分钟
- C_1.30m_Jumpers      1.30m - 120 分钟
- C_1.40m_Jumpers      1.40m - 120 分钟
- C_1.20m_Derby        1.20m - 180 分钟
- C_1.35m_Derby        1.35m - 180 分钟
- C_1.45m_Derby        1.45m - 180 分钟
- C_1.40m_Open         1.40m - 120 分钟
- C_1.50m_Open         1.50m - 180 分钟
- C_1.60m_Grand_Prix   1.60m - 240 分钟
"""

import dataclasses
from absl import app
import numpy as np
from ortools.sat.python import cp_model


@dataclasses.dataclass(frozen=True)
class Arena:
    """单个场地的数据。"""

    id: str
    hours: str


@dataclasses.dataclass(frozen=True)
class Competition:
    """单场比赛的数据。"""

    id: str
    height: float
    duration: int


@dataclasses.dataclass(frozen=True)
class HorseJumpingShowData:
    """马术场地障碍赛的全部输入数据。"""

    num_days: int
    competitions: list[Competition]
    arenas: list[Arena]


@dataclasses.dataclass(frozen=True)
class ScheduledCompetition:
    """马术场地障碍赛的一条赛程结果。"""

    completion: str
    day: int
    arena: str
    start_time: str
    end_time: str


def generate_horse_jumping_show_data() -> HorseJumpingShowData:
    """生成马术场地障碍赛的数据。"""
    # 场地列表：名称与开放时段（AM/PM 字符串）。
    arenas = [
        Arena(id="Main Stage", hours="9AM-9PM"),
        Arena(id="Highlands", hours="9AM-5PM"),
        Arena(id="Sawdust", hours="9AM-5PM"),
    ]
    # 比赛列表：编号、障碍高度（米）、时长（分钟）。
    competitions = [
        Competition(id="C_5_1.10m_Year_Olds", height=1.1, duration=60),
        Competition(id="C_6_1.25m_Year_Olds", height=1.25, duration=90),
        Competition(id="C_7_1.35m_Year_Olds", height=1.35, duration=120),
        Competition(id="C_0.8m_Jumpers", height=0.8, duration=240),
        Competition(id="C_1.0m_Jumpers", height=1.0, duration=180),
        Competition(id="C_1.10m_Jumpers", height=1.10, duration=180),
        Competition(id="C_1.20m_Jumpers", height=1.20, duration=120),
        Competition(id="C_1.30m_Jumpers", height=1.30, duration=120),
        Competition(id="C_1.40m_Jumpers", height=1.40, duration=120),
        Competition(id="C_1.20m_Derby", height=1.20, duration=180),
        Competition(id="C_1.35m_Derby", height=1.35, duration=180),
        Competition(id="C_1.45m_Derby", height=1.45, duration=180),
        Competition(id="C_1.40m_Open", height=1.40, duration=120),
        Competition(id="C_1.50m_Open", height=1.50, duration=180),
        Competition(id="C_1.60m_Grand_Prix", height=1.60, duration=240),
    ]
    return HorseJumpingShowData(num_days=3, competitions=competitions, arenas=arenas)


def solve() -> list[ScheduledCompetition]:
    """求解马术场地障碍赛排期问题。"""
    data = generate_horse_jumping_show_data()
    num_days = data.num_days
    competitions = data.competitions
    arenas = data.arenas
    day_index = list(range(num_days))

    # 时间解析器：把 "9AM"/"9PM" 之类的字符串解析成当天分钟数。
    def parse_time(t_str):
        hour = int(t_str[:-2])
        if "PM" in t_str and hour != 12:
            hour += 12
        if "AM" in t_str and hour == 12:
            hour = 0
        return hour * 60

    # 为每个场地计算可排赛的时段区间 [开始分钟, 结束分钟]。
    schedule_interval_by_arena = {}
    for arena in arenas:
        start_h_str, end_h_str = arena.hours.split("-")
        start_time = parse_time(start_h_str)
        end_time = parse_time(end_h_str)
        schedule_interval_by_arena[arena.id] = (start_time, end_time)

    # 时间与 30 分钟时间槽之间的相互换算。
    time_slot_size = 30

    def time_to_slot(time_in_minutes: int):
        # 分钟数 -> 时间槽编号。
        return time_in_minutes // time_slot_size

    def slot_to_time(slot_index: int):
        # 时间槽编号 -> 分钟数。
        return slot_index * time_slot_size

    # --- 创建模型 ---
    model = cp_model.CpModel()

    # --- 变量 ---
    # 按（比赛, 场地, 天）三维组织变量：布尔变量表示该组合是否被选中。
    competition_assignments = np.empty(
        (len(competitions), len(arenas), num_days), dtype=object
    )
    for c, comp in enumerate(competitions):
        for a, arena in enumerate(arenas):
            for d in day_index:
                competition_assignments[c, a, d] = model.new_bool_var(
                    f"competition_scheduled_{comp.id}_{arena.id}_{d}"
                )
    # 每场比赛的开始时间与时间区间。这里用 0,1,2,... 这样的时间步（30 分钟
    # 一格）来表示开始时间，而不是直接用分钟数表示。
    competition_start_times = np.empty(
        (len(competitions), len(arenas), num_days), dtype=object
    )
    competition_intervals = np.empty(
        (len(competitions), len(arenas), num_days), dtype=object
    )
    for c, comp in enumerate(competitions):
        for a, arena in enumerate(arenas):
            earliest_start_time, latest_end_time = schedule_interval_by_arena[arena.id]
            # 最晚开始时间 = 场地关闭时间 - 比赛时长。
            latest_start_time = latest_end_time - comp.duration
            for d in day_index:
                # 开始时间槽变量，范围由场地开放时段与比赛时长决定。
                competition_start_times[c, a, d] = model.new_int_var(
                    time_to_slot(earliest_start_time),
                    time_to_slot(latest_start_time),
                    f"start_time_{comp.id}_{arena.id}_{d}",
                )
                # 可选定长区间变量：仅当对应的分配布尔变量为真时才"存在"，
                # 长度为比赛时长（换算成时间槽数）。
                competition_intervals[c, a, d] = (
                    model.new_optional_fixed_size_interval_var(
                        competition_start_times[c, a, d],
                        time_to_slot(comp.duration),
                        competition_assignments[c, a, d],
                        f"task_{comp.id}_{arena.id}_{d}",
                    )
                )

    # --- 约束 ---
    # 每场比赛都必须被安排恰好一次；同时初学者比赛安排在第一天、
    # 高级比赛安排在最后一天。
    for c, comp in enumerate(competitions):
        # 三维数组求和为 1：比赛只在一个 (场地, 天) 组合上举办。
        model.add(np.sum(competition_assignments[c, :, :]) == 1)
        # 初学者比赛（高度 <= 1.10m）必须在第一天。
        if comp.height <= 1.10:
            beginners_day = 0
            model.add(np.sum(competition_assignments[c, :, beginners_day]) == 1)
        # 高级比赛（高度 >= 1.50m）必须在最后一天。
        if comp.height >= 1.50:
            advanced_day = num_days - 1
            model.add(np.sum(competition_assignments[c, :, advanced_day]) == 1)

    # 同一场地、同一天安排的比赛不能重叠。
    for a, _ in enumerate(arenas):
        for day in range(num_days):
            model.add_no_overlap(competition_intervals[:, a, day])

    # 各比赛的开始时间应分散在全天（同场地同天开始时间两两不同）。
    for a, _ in enumerate(arenas):
        for day in day_index:
            model.add_all_different(competition_start_times[:, a, day])

    # --- 目标函数 ---
    # 最大化所有开始时间之和：让比赛尽量安排在较晚的时段。
    model.maximize(np.sum(competition_start_times))

    # --- 求解 ---
    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = 30.0
    solver.parameters.log_search_progress = True
    solver.parameters.num_workers = 16
    status = solver.solve(model)

    # --- 打印解 ---
    if status == cp_model.OPTIMAL or status == cp_model.FEASIBLE:
        schedule = []
        # 遍历天/比赛/场地，还原被选中的 (比赛, 场地, 天) 组合及开始时间。
        for day in range(num_days):
            for c, comp in enumerate(competitions):
                for a, arena in enumerate(arenas):
                    if solver.value(competition_assignments[c, a, day]):
                        start_time_minutes = slot_to_time(
                            solver.value(competition_start_times[c, a, day])
                        )
                        # 把分钟数格式化为 "HH:MM" 的起止时间。
                        start_h, start_m = divmod(start_time_minutes, 60)
                        end_h, end_m = divmod(start_time_minutes + comp.duration, 60)
                        schedule.append(
                            ScheduledCompetition(
                                completion=comp.id,
                                day=day + 1,
                                arena=arena.id,
                                start_time=f"{start_h:02d}:{start_m:02d}",
                                end_time=f"{end_h:02d}:{end_m:02d}",
                            )
                        )
        # 按日期和开始时间排序后打印，便于阅读。
        schedule.sort(key=lambda x: (x.day, x.start_time))
        print("Schedule:")
        for item in schedule:
            print(
                f"Day {item.day}:  {item.completion} in {item.arena} from"
                f" {item.start_time} to {item.end_time}."
            )
        return schedule
    elif status == cp_model.INFEASIBLE:
        print("Problem is infeasible.")
    else:
        print("No solution found.")
    # 未找到解时返回空赛程表。
    return []


def main(_):
    solve()


if __name__ == "__main__":
    app.run(main)
