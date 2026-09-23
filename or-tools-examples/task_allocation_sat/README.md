# task_allocation_sat（任务时间槽分配问题）

用 CP-SAT 把所有任务分配到可用时间槽中，使**被使用的时间槽数量最少**（每个时间槽容量有限）。

## 问题描述

这是一个任务排程/时间槽分配问题（源自博客文章《MiniZinc/CP-SAT vs MIP》的对比案例）：

- 有 `ntasks` 个任务（由 `available` 可用性矩阵的行数给出）和 `nslots` 个时间槽（列数，本例为 50）。
- `available[task][slot] = 1` 表示任务 task 可以被安排在时间槽 slot（任务各有自己的可用窗口，互不相同）。
- 每个任务必须且只能分配到**一个**它可用的时间槽中。
- 每个时间槽的容量为 `capacity = 3`：同一时间槽最多容纳 3 个任务。

**输入**：代码内置的 30×50 可用性矩阵（每行是一段连续的 1，表示各任务可用的时间窗口）与槽容量。

**要求**：把所有任务分配出去，最小化**被使用（至少含一个任务）的时间槽个数**——占用的时间槽越少，资源/人力浪费越小。

## 建模思路

模型构建在 `task_allocation_sat()` 函数中：

**决策变量**

- `assign[(task, slot)]`：布尔变量，任务 task 是否分配到时间槽 slot（`new_bool_var`）；
- `count`：被使用的时间槽个数，域 `[0, nslots]`；
- `slot_used[s]`：布尔变量，时间槽 s 是否被使用。

**约束条件**

1. **任务唯一分配**：对每个任务 task，`sum(assign[(task, slot)] for 可用 slot) == 1`——每个任务恰好分配到一个其可用的时间槽。
2. **槽容量约束**：对每个时间槽 slot，`sum(assign[(task, slot)] for 可用 task) <= capacity`——槽内任务数不超过 3。
3. **槽使用标记**：`add_bool_or(可用任务的 assign 变量).only_enforce_if(slot_used[slot])`——若槽被标记为"已使用"，则至少有一个任务分配到该槽；同时对可用任务添加 `add_implication(~slot_used[slot], ~assign[...])`（槽未使用则任务不能分入），对不可用任务直接 `add(assign[(task, slot)] == 0)`。
4. **计数关联**：`count == sum(slot_used)`。
5. （代码中被注释掉的）冗余下界约束 `count >= ceil(nslots / capacity)`，作者注明加入该约束可让本实例更容易求解。

**目标函数**

`model.minimize(count)`——最小化被使用的时间槽个数。

## 运行方法

```bash
python3 task_allocation_sat.py
```

代码中**没有定义任何 absl flags**。默认行为：求解内置的 30 任务 × 50 时间槽实例（容量 3），开启搜索日志（`log_search_progress = True`）并使用 16 个并行搜索 worker（`num_search_workers = 16`）；命令行传入多余参数会抛出 `app.UsageError`。求解完成后程序结束（代码中未打印解明细，结果通过求解日志观察）。

## 关键实现说明

- **代码结构**：单文件单函数结构；`task_allocation_sat()` 内置 `available` 数据矩阵并完成建模与求解；`main()` 校验命令行参数后调用。
- **关键 API**：
  - `cp_model.CpModel()`：创建模型；
  - `model.new_bool_var(name)`：创建布尔分配变量 `assign[(task, slot)]` 与槽使用标记 `slot_used[s]`；
  - `model.new_int_var(0, nslots, "count")`：创建被使用槽计数变量；
  - `model.add(expr)`：添加线性约束（唯一分配、容量、计数关联）；
  - `model.add_bool_or(...).only_enforce_if(lit)`：条件子句——在 `slot_used[slot]` 为真时至少一个任务在该槽；
  - `model.add_implication(a, b)`：布尔蕴涵（槽未使用 ⇒ 任务不能分入）；
  - `model.add(assign[(task, slot)] == 0)`：把不可用组合固定为 0；
  - `model.minimize(count)`：设定目标；`solver.parameters.num_search_workers / log_search_progress`：配置并行 worker 与日志。
- **技术要点**：
  - "最小化使用的槽数"建模为 `count == sum(slot_used)` 后直接最小化；
  - `add_bool_or(...).only_enforce_if(...)` 与蕴涵结合，正确地把"使用"标记与槽内任务数绑定；
  - 源自 yetanothermathprogrammingconsultant 博客的 MiniZinc/CP-SAT 与 MIP 对比实例，可作为建模技巧对照案例。
