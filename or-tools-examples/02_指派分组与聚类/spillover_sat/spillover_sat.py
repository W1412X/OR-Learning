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

"""求解购买物理机以满足虚拟机（VM）需求的 Spillover 问题。

Spillover 问题的定义如下：

假设有 M 种类型的物理机和 V 种类型的虚拟机（VM）。使用一台第 m 类型的
物理机可以获得 n_mv 台 VM v。每种类型的物理机成本为 c_m。每种 VM 的需
求量为 d_v。VM 按如下规则分配到物理机上：每种 VM 类型的需求在区间 [0, 1]
内等间隔到达。对于每种 VM 类型，必须遵循一个物理机类型的优先级顺序。当需
求到达时，若最高优先级的机器类型仍有可用机器，则先使用它们，然后再转向第
二优先级的机器类型，依此类推。每种 VM 类型有一个兼容的物理机类型列表，当
该列表耗尽时，剩余需求无法满足。目标是选择购买各类物理机的数量（最小化成
本），使得所有 VM 的总需求中至少某个目标服务水平（例如 95%）被满足。

所购买的各类型机器的数量以及各类型 VM 的需求量都足够大，因此如果有帮助，
可以转而求解一个近似问题：允许购买数量以及机器到 VM 的分配为分数（连续）
值。

该问题孤立地看并不特别有趣，更有趣的是将其中的 LP 嵌入到更大的优化问题中
（例如考虑一个两阶段问题：第一阶段购买机器，第二阶段实现 VM 需求）。

该问题的连续近似可以用 LP 求解（参见 MathOpt Python 示例）。这样做而不使
用 MIP 并非易事。下面我们展示：尽管 CP-SAT 没有连续变量，该连续松弛问题
仍然可以用 CP-SAT 近似求解。如果孤立地求解该问题，应当直接使用 LP 求解
器；但如果要增加附加约束或将该模型嵌入更复杂的问题中，使用 CP-SAT 可能更
合适。

如果对于每种 VM 类型，性价比最高的物理机恰好是最高优先级的机器类型，并且
目标服务水平为 100%，那么该问题有一个平凡的最优解：
  1. 按"使用第 1 优先机器类型满足单位需求的成本"从低到高对 VM 排序。
  2. 按上述顺序处理每种 VM 类型，不断购买第 1 优先机器类型的机器，直到
     该 VM 类型的全部需求得到满足。

MOE:begin_strip
本示例由 Cloudy 问题启发，参见 go/fluid-model。
MOE:end_strip
"""

from collections.abc import Sequence
import dataclasses
import math
import random

from absl import app
from absl import flags
from ortools.sat.python import cp_model

# 以下是本脚本的 absl 命令行参数（flags）。
# 可用于满足需求的机器类型数量。
_MACHINE_TYPES = flags.DEFINE_integer(
    "machine_types",
    100,
    "How many types of machines we can fulfill demand with.",
)

# 需要供应的 VM 类型数量。
_VM_TYPES = flags.DEFINE_integer(
    "vm_types", 500, "How many types of VMs we need to supply."
)

# 每种 VM 可由多少种机器类型满足（随机均匀选取）。
_FUNGIBILITY = flags.DEFINE_integer(
    "fungibility",
    10,
    "Each VM type can be satisfied with this many machine types, selected"
    " uniformly at random.",
)

# 每种 VM 的需求量在 [max_demand//2, max_demand] 内均匀随机。
_MAX_DEMAND = flags.DEFINE_integer(
    "max_demand",
    100,
    "Demand for each VM type is in [max_demand//2, max_demand], uniformly at"
    " random.",
)

# 是否使用小型测试实例代替随机数据。
_TEST_DATA = flags.DEFINE_bool(
    "test_data", False, "Use small test instance instead of random data."
)

# 生成实例的随机数种子。
_SEED = flags.DEFINE_integer("seed", 13, "RNG seed for instance creation.")

# 时间离散化的步数（时间视界 T）。
_TIME_STEPS = flags.DEFINE_integer("time_steps", 100, "How much to discretize time.")


@dataclasses.dataclass(frozen=True)
class MachineUse:
    """一种机器对某种 VM 的可用性描述。"""

    # 机器类型编号 j。
    machine_type: int
    # 一台该类型机器可承载的 VM 数量 n_ij。
    vms_per_machine: int


@dataclasses.dataclass(frozen=True)
class VmDemand:
    """一种 VM 的需求数据。"""

    # 兼容的物理机类型列表（按优先级排列），列表按优先级顺序被依次使用。
    compatible_machines: tuple[MachineUse, ...]
    # 该 VM 类型的总需求量 d_i。
    vm_quantity: int


@dataclasses.dataclass(frozen=True)
class SpilloverProblem:
    """完整的 Spillover 问题实例。"""

    # 每种机器类型的成本 c_j。
    machine_cost: tuple[float, ...]
    # 每种机器类型可购买的数量上限 l_j。
    machine_limit: tuple[int, ...]
    # 每种 VM 的需求（含兼容机器列表与需求量）。
    vm_demands: tuple[VmDemand, ...]
    # 目标服务水平：需要满足的需求比例。
    service_level: float
    # 时间离散化的总步数 T。
    time_horizon: int


def _random_spillover_problem(
    num_machines: int,
    num_vms: int,
    fungibility: int,
    max_vm_demand: int,
    horizon: int,
) -> SpilloverProblem:
    """生成一个随机的 SpilloverProblem 实例。"""
    # 每种机器的成本在 (0, 1) 内均匀随机。
    machine_costs = tuple(random.random() for _ in range(num_machines))
    vm_demands = []
    all_machines = list(range(num_machines))
    min_vm_demand = max_vm_demand // 2
    for _ in range(num_vms):
        vm_use = []
        # 每种 VM 随机选取 fungibility 种兼容机器类型，承载能力在 [1, 10] 内随机。
        for machine in random.sample(all_machines, fungibility):
            vm_use.append(
                MachineUse(machine_type=machine, vms_per_machine=random.randint(1, 10))
            )
        vm_demands.append(
            VmDemand(
                compatible_machines=tuple(vm_use),
                # 需求量在 [min_vm_demand, max_vm_demand] 内均匀随机。
                vm_quantity=random.randint(min_vm_demand, max_vm_demand),
            )
        )
    # 机器购买上限取足够大的值（能装下全部需求），使上限不起约束作用。
    machine_need_ub = num_vms * max_vm_demand
    machine_limit = (machine_need_ub,) * num_machines
    return SpilloverProblem(
        machine_cost=machine_costs,
        machine_limit=machine_limit,
        vm_demands=tuple(vm_demands),
        # 目标服务水平固定为 95%。
        service_level=0.95,
        time_horizon=horizon,
    )


def _test_problem() -> SpilloverProblem:
    """创建一个小型 SpilloverProblem 实例，最优目标值为 360。"""
    # 为避免使用机器类型 2，需购买足够多的机器 1 以免缺货，成本 20。
    vm_a = VmDemand(
        vm_quantity=10,
        compatible_machines=(
            MachineUse(machine_type=1, vms_per_machine=1),
            MachineUse(machine_type=2, vms_per_machine=1),
        ),
    )
    # 机器类型 0 更便宜，但不想让机器类型 1 缺货，于是全部用机器类型 1，
    # 成本 40。
    vm_b = VmDemand(
        vm_quantity=20,
        compatible_machines=(
            MachineUse(machine_type=1, vms_per_machine=1),
            MachineUse(machine_type=0, vms_per_machine=1),
        ),
    )
    # 只能用机器类型 2，需要 3 台，成本 300。
    vm_c = VmDemand(
        vm_quantity=30,
        compatible_machines=(MachineUse(machine_type=2, vms_per_machine=10),),
    )
    return SpilloverProblem(
        machine_cost=(1.0, 2.0, 100.0),
        machine_limit=(60, 60, 60),
        vm_demands=(vm_a, vm_b, vm_c),
        service_level=1.0,
        time_horizon=100,
    )


# 下标集合：
#  * i in I：VM 需求
#  * j in J：机器供应
#
# 数据：
#  * c_j：第 j 类机器的成本
#  * l_j：第 j 类机器可购买的数量上限
#  * n_ij：一台第 j 类机器可承载的 VM i 的数量
#  * d_i：VM i 的总需求
#  * service_level：需要满足的需求比例（目标服务水平）
#  * P_i subset J：VM 需求 i 的兼容机器类型集合
#  * UP_i(j) subset P_i, for j in P_i：对 VM 需求 i 而言，优先级高于 j
#    的机器集合
#  * T：整数时间步数
#
# 注意：当 d_i/n_ij 不是整数时，下文约束 6 会引入一些近似误差。
#
# 决策变量：
#  * s_j：第 j 类机器的购买量（供应）
#  * w_j：第 j 类机器被用光的时刻；若永不耗尽则为 1（时间归一化意义下）
#  * v_ij：开始使用机器 j 满足需求 i 的时刻；若永不用该机器满足该需求，
#          则等于 w_j
#  * o_i：VM 需求 i 开始无法满足的时刻
#  * m_i：VM i 被满足的总需求量
#
# 模型形式：
#   min   sum_{j in J} c_j s_j
#   s.t.
#     1:  sum_i m_i >= service_level * sum_{i in I} d_i
#     2:  T * m_i <= o_i * d_i                                    for all i in I
#     3:  v_ij >= w_r                     for all i in I, j in C_i, r in UP_i(j)
#     4:  v_ij <= w_j                                   for all i in I, j in C_i
#     5:  o_i = sum_{j in P_i} (w_j - v_ij)                       for all i in I
#     6:  sum_{i in I: j in P_i}ceil(d_i/n_ij)(w_j - v_ij)<=T*s_j for all j in J
#         o_i, w_j, v_ij in [0, T]
#         0 <= m_i <= d_i
#         0 <= s_j <= l_j
#
# 各条约束的含义：
#  1. 被满足的需求量至少为总需求的 95%（service_level 比例）。
#  2. VM i 被满足的需求量与"停止服务的时间"呈线性关系。
#  3. 在所有更高优先级的机器类型 r 耗尽之前，不得开始用机器 j 满足需求 i。
#  4. 机器 j 的耗尽时刻必须不早于开始用它满足 VM 需求 i 的时刻。
#  5. 无法继续满足 VM 需求 i 的时刻，等于用每个可用机器类型服务所花费的
#     时间之和。
#  6. 用机器 j 满足需求的总使用量不超过其供应量。当 d_i/n_ij 不是整数时，
#     上式中的 ceil 函数会引入一些近似误差。
def _solve_spillover_problem(problem: SpilloverProblem) -> None:
    """求解 Spillover 问题并打印最优目标值。"""
    model = cp_model.CpModel()
    num_machines = len(problem.machine_cost)
    num_vms = len(problem.vm_demands)
    horizon = problem.time_horizon
    # 决策变量 s_j：购买第 j 类机器的数量（0 ~ machine_limit[j]）。
    s = [
        model.new_int_var(lb=0, ub=problem.machine_limit[j], name=f"s_{j}")
        for j in range(num_machines)
    ]
    # 决策变量 w_j：第 j 类机器被用光的时刻（0 ~ T）。
    w = [
        model.new_int_var(lb=0, ub=horizon, name=f"w_{i}") for i in range(num_machines)
    ]
    # 决策变量 o_i：VM 需求 i 开始断供的时刻（0 ~ T）。
    o = [model.new_int_var(lb=0, ub=horizon, name=f"o_{j}") for j in range(num_vms)]
    # 决策变量 m_i：VM i 被满足的需求总量（0 ~ d_i）。
    m = [
        model.new_int_var(lb=0, ub=problem.vm_demands[j].vm_quantity, name=f"m_{j}")
        for j in range(num_vms)
    ]
    # 决策变量 v_ij：开始用机器 j 满足需求 i 的时刻（0 ~ T），
    # 以字典形式按 VM 下标 i 组织，键为机器类型编号。
    v = [
        {
            compat.machine_type: model.new_int_var(
                lb=0, ub=horizon, name=f"v_{i}_{compat.machine_type}"
            )
            for compat in vm_demand.compatible_machines
        }
        for i, vm_demand in enumerate(problem.vm_demands)
    ]

    # 目标函数：最小化采购总成本 sum_j c_j * s_j。
    obj = 0
    for j in range(num_machines):
        obj += s[j] * problem.machine_cost[j]
    model.minimize(obj)

    # 约束 1：被满足的需求量至少为总需求量的 service_level 比例。
    total_vm_demand = sum(vm_demand.vm_quantity for vm_demand in problem.vm_demands)
    model.add(sum(m) >= int(math.ceil(problem.service_level * total_vm_demand)))

    # 约束 2：被满足的需求量与断供时间呈线性关系。
    for i in range(num_vms):
        model.add(
            problem.time_horizon * m[i] <= o[i] * problem.vm_demands[i].vm_quantity
        )

    # 约束 3：在所有更高优先级的机器类型 r 耗尽之前，
    # 不得开始用机器类型 j 满足需求 i。
    for i in range(num_vms):
        for k, meet_demand in enumerate(problem.vm_demands[i].compatible_machines):
            j = meet_demand.machine_type
            for l in range(k):
                r = problem.vm_demands[i].compatible_machines[l].machine_type
                model.add(v[i][j] >= w[r])

    # 约束 4：机器 j 的断供（耗尽）时刻不早于开始用它满足 VM 需求 i 的时刻。
    for i in range(num_vms):
        for meet_demand in problem.vm_demands[i].compatible_machines:
            j = meet_demand.machine_type
            model.add(v[i][j] <= w[j])

    # 约束 5：对 VM 需求 i，服务结束的时刻等于
    # 用每个可用机器类型服务所花费的时间之和。
    for i in range(num_vms):
        sum_serving = 0
        for meet_demand in problem.vm_demands[i].compatible_machines:
            j = meet_demand.machine_type
            sum_serving += w[j] - v[i][j]
        model.add(o[i] == sum_serving)

    # 约束 6：机器类型 j 的总使用量不超过其供应量。
    #
    # 数据按 VM 组织（转置关系），因此在这里批量构造各机器的约束。
    total_machine_use = [0 for _ in range(num_machines)]
    for i in range(num_vms):
        for meet_demand in problem.vm_demands[i].compatible_machines:
            j = meet_demand.machine_type
            nij = meet_demand.vms_per_machine
            vm_quantity = problem.vm_demands[i].vm_quantity
            # 需要 vm_quantity/nij 台机器，为使用整数系数，
            # 用 ceil(vm_quantity/nij) 高估。
            rate = (vm_quantity + nij - 1) // nij
            total_machine_use[j] += rate * (w[j] - v[i][j])
    for j in range(num_machines):
        model.add(total_machine_use[j] <= horizon * s[j])

    # 创建求解器并求解。
    solver = cp_model.CpSolver()
    solver.parameters.num_workers = 16
    solver.parameters.log_search_progress = True
    solver.max_time_in_seconds = 30.0
    status = solver.solve(model)
    # 期望得到最优解，否则报错。
    if status != cp_model.OPTIMAL:
        raise RuntimeError(f"expected optimal, found: {status}")
    print(f"objective: {solver.objective_value}")


def main(argv: Sequence[str]) -> None:
    del argv  # 未使用。
    # 以指定种子初始化随机数生成器，保证实例可复现。
    random.seed(_SEED.value)
    if _TEST_DATA.value:
        problem = _test_problem()
    else:
        problem = _random_spillover_problem(
            _MACHINE_TYPES.value,
            _VM_TYPES.value,
            _FUNGIBILITY.value,
            _MAX_DEMAND.value,
            _TIME_STEPS.value,
        )
    print(problem)

    _solve_spillover_problem(problem)


if __name__ == "__main__":
    app.run(main)
