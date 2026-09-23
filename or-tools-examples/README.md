# OR-Tools Python 示例中文讲解集

本目录整理自 `or-tools-9.15/examples/python/` 中的全部 **60 个** Python 示例，每个示例一个独立文件夹，包含：

- `README.md`：示例主题、问题描述（现实情景）、建模思路（决策变量 / 约束 / 目标函数）、运行方法（含命令行参数表）、关键实现说明。
- `<示例名>.py`：完整源代码，注释已全部中文化（可执行代码与官方源码保持一致）。

运行任何示例前请先安装：

```bash
python3 -m pip install --upgrade --user ortools
```

## 目录索引

### 入门与基础 API

| 示例 | 主题 | 技术 |
| --- | --- | --- |
| [nqueens_sat](nqueens_sat) | N 皇后问题，枚举全部解 | CP-SAT |
| [sudoku_sat](sudoku_sat) | 数独求解器 | CP-SAT |
| [linear_programming](linear_programming) | 线性规划入门，双 API 风格 | pywraplp（GLOP/GLPK/CLP/PDLP/XPRESS） |
| [integer_programming](integer_programming) | 整数规划入门 | pywraplp（GLPK/SCIP/SAT/XPRESS） |
| [linear_assignment_api](linear_assignment_api) | 最小成本指派 | SimpleLinearSumAssignment |
| [pyflow_example](pyflow_example) | 最大流 / 最小费用流 | graph 库（pyflow） |
| [proto_solve](proto_solve) | 从 MPS 文件加载模型求解 | model_builder |
| [transit_time](transit_time) | 配送路线行驶 / 服务时间展示 | 纯计算演示 |

### 指派 / 分组 / 聚类

| 示例 | 主题 | 技术 |
| --- | --- | --- |
| [assignment_with_constraints_sat](assignment_with_constraints_sat) | 带工人组合约束的指派 | CP-SAT |
| [task_allocation_sat](task_allocation_sat) | 任务-时间槽分配，最少时间槽 | CP-SAT |
| [tasks_and_workers_assignment_sat](tasks_and_workers_assignment_sat) | 任务工人分组，最小化最大人均成本 | CP-SAT |
| [balance_group_sat](balance_group_sat) | 等大小组的分组平衡 | CP-SAT |
| [clustering_sat](clustering_sat) | 城市聚类，最小化组内距离 | CP-SAT |
| [wedding_optimal_chart_sat](wedding_optimal_chart_sat) | 婚礼座位安排 | CP-SAT |
| [maximize_combinations_sat](maximize_combinations_sat) | 选卡片最大化有效组合数 | CP-SAT |
| [reallocate_sat](reallocate_sat) | 年度产量再均衡 | CP-SAT |
| [spillover_sat](spillover_sat) | 采购物理机满足 VM 需求（溢出） | CP-SAT |

### 调度 / 排班 / 排产

| 示例 | 主题 | 技术 |
| --- | --- | --- |
| [flexible_job_shop_sat](flexible_job_shop_sat) | 柔性作业车间调度（可选机器） | CP-SAT |
| [jobshop_ft06_sat](jobshop_ft06_sat) | 标准 ft06 作业车间调度 | CP-SAT |
| [jobshop_ft06_distance_sat](jobshop_ft06_distance_sat) | ft06 变体：机器上任务最小间隔 | CP-SAT |
| [jobshop_with_maintenance_sat](jobshop_with_maintenance_sat) | 带机器维护时段的作业车间 | CP-SAT |
| [rcpsp_sat](rcpsp_sat) | 资源受限项目调度（RCPSP） | CP-SAT |
| [shift_scheduling_sat](shift_scheduling_sat) | 员工轮班排班 | CP-SAT |
| [vendor_scheduling_sat](vendor_scheduling_sat) | 商贩 x 时段班次选择排班 | CP-SAT |
| [bus_driver_scheduling_sat](bus_driver_scheduling_sat) | 公交司机排班（逐司机路径模型） | CP-SAT |
| [bus_driver_scheduling_flow_sat](bus_driver_scheduling_flow_sat) | 公交司机排班（流网络模型） | CP-SAT |
| [no_wait_baking_scheduling_sat](no_wait_baking_scheduling_sat) | 面包店无等待烘焙调度 | CP-SAT |
| [single_machine_scheduling_with_setup_release_due_dates_sat](single_machine_scheduling_with_setup_release_due_dates_sat) | 带换型 / 释放 / 交货期的单机调度 | CP-SAT |
| [weighted_latency_problem_sat](weighted_latency_problem_sat) | 加权延迟问题 | CP-SAT |
| [line_balancing_sat](line_balancing_sat) | 装配线平衡（SALBP） | CP-SAT |
| [car_sequencing_optimization_sat](car_sequencing_optimization_sat) | 汽车排序（滑动窗口产能） | CP-SAT |
| [appointments](appointments) | 预约会期安排（两阶段） | CP-SAT |
| [horse_jumping_show](horse_jumping_show) | 马术障碍赛排期 | CP-SAT |
| [gate_scheduling_sat](gate_scheduling_sat) | 闸门调度（共享宽度上限） | CP-SAT |
| [test_scheduling_sat](test_scheduling_sat) | 电源功率约束下的测试调度 | CP-SAT |

### 路径 / 网络

| 示例 | 主题 | 技术 |
| --- | --- | --- |
| [tsp_sat](tsp_sat) | TSP 旅行商问题 | CP-SAT（add_circuit） |
| [random_tsp](random_tsp) | 随机 TSP | Routing 库 |
| [prize_collecting_tsp](prize_collecting_tsp) | 奖赏收集 TSP | Routing 库 |
| [prize_collecting_tsp_sat](prize_collecting_tsp_sat) | 奖赏收集 TSP | CP-SAT |
| [prize_collecting_vrp](prize_collecting_vrp) | 奖赏收集 VRP（多车辆） | Routing 库 |
| [prize_collecting_vrp_sat](prize_collecting_vrp_sat) | 奖赏收集 VRP（多车辆） | CP-SAT |
| [maze_escape_sat](maze_escape_sat) | 3D 迷宫按序取宝哈密顿路径 | CP-SAT（add_circuit） |

### 装箱 / 布局 / 二维几何

| 示例 | 主题 | 技术 |
| --- | --- | --- |
| [knapsack_2d_sat](knapsack_2d_sat) | 二维矩形背包（三种建模技术） | CP-SAT |
| [cover_rectangle_sat](cover_rectangle_sat) | 最少正方形铺满矩形 | CP-SAT |
| [memory_layout_and_infeasibility_sat](memory_layout_and_infeasibility_sat) | 内存布局 + 最小冲突集（不可行诊断） | CP-SAT |
| [steel_mill_slab_sat](steel_mill_slab_sat) | 钢铁厂板坯问题（三种建模技术） | CP-SAT |
| [arc_flow_cutting_stock_sat](arc_flow_cutting_stock_sat) | 弧流下料问题 | CP-SAT + SCIP |

### 数独之外的谜题与数学

| 示例 | 主题 | 技术 |
| --- | --- | --- |
| [cryptarithm_sat](cryptarithm_sat) | 字谜算术 SEND+MORE=MONEY | CP-SAT |
| [zebra_sat](zebra_sat) | 斑马逻辑谜题 | CP-SAT |
| [hidato_sat](hidato_sat) | Hidato 数字蛇填数谜题 | CP-SAT |
| [pentominoes_sat](pentominoes_sat) | 五格骨牌铺砌 | CP-SAT |
| [golomb_sat](golomb_sat) | Golomb 尺 | CP-SAT |
| [golomb8](golomb8) | 8 刻度 Golomb 尺 | 经典 pywrapcp |
| [pell_equation_sat](pell_equation_sat) | 佩尔方程 x² − c·y² = 1 | CP-SAT |
| [magic_sequence_distribute](magic_sequence_distribute) | 魔幻序列 | 经典 pywrapcp（Distribute） |
| [spread_robots_sat](spread_robots_sat) | 机器人两两距离最大化 | CP-SAT |
| [qubo_sat](qubo_sat) | QUBO 二次二值优化 | CP-SAT |
| [chemical_balance_sat](chemical_balance_sat) | 化学配料平衡（养分短缺最小化） | CP-SAT |
| [chemical_balance_lp](chemical_balance_lp) | 化肥配比 LP | GLOP |
| [music_playlist_sat](music_playlist_sat) | 均衡音乐播放列表 | CP-SAT |

## 说明

- 各示例的可执行代码与官方源码逐行一致，仅注释 / docstring 已汉化；如需对照原版请查看 `or-tools-9.15/examples/python/`。
- 部分示例需要 `absl-py`（随 ortools 一起安装）；少数示例还依赖 `pandas` 等第三方库，详见对应 README。
- `weighted_latency_problem_sat` 使用了 9.15 新增的 `parse_text_format` API，需 ortools 9.15 及以上版本运行。
