# proto_solve

从 MPS 文件加载优化模型，并用 OR-Tools 的 `model_builder`（ModelBuilder / ModelSolver API）选择求解器进行求解。

## 问题描述

实际业务中，优化模型常常由外部工具（如 GUROBI/CPLEX 的模型导出、AMPL、PuLP 等）生成并保存为 **MPS 格式**（行业标准数学规划文件格式，可表达线性规划 / 整数规划模型）。本示例提供一个通用的"命令行求解器"：

- 输入：一个 MPS 模型文件路径（flag `--input`），可选求解器类型（flag `--solver`）与求解器参数字符串（flag `--params`）。
- 要求：读取 MPS 文件构建模型，选择指定后端求解器求解，并开启求解日志输出。
- 结果：求解结果直接由求解器以日志形式输出（变量取值、目标值等）。若 MPS 文件导入失败，打印 `Cannot import MPS file: '...'` 并退出；若指定的求解器不受支持，打印 `Cannot create solver with name '...'` 并退出。

## 建模思路

本示例**不在代码中手工建模**，模型完全来自 MPS 文件（由 `import_from_mps_file` 解析：目标函数、约束、变量及其类型都定义在文件里）。代码职责是"加载 → 校验求解器 → 设置参数 → 求解"四个步骤：

1. `model_builder.ModelBuilder()` 创建空的模型构建器；
2. `model.import_from_mps_file(path)` 从 MPS 文件导入模型（返回 False 表示失败）；
3. `model_builder.ModelSolver(name)` 按名称创建求解器（默认 `'sat'`，即 CP-SAT；也可指定其他受支持的后端），用 `solver_is_supported()` 校验；
4. `solver.set_solver_specific_parameters(params)` 设置求解器专有参数（原样传递字符串）；
5. `solver.enable_output(True)` 开启日志输出；
6. `solver.solve(model)` 执行求解。

## 运行方法

```bash
python3 proto_solve.py --input=model.mps --solver=sat --params=''
```

absl flag 参数：

| 参数 | 默认值 | 含义 |
| --- | --- | --- |
| `--input` | `''`（空） | 要加载并求解的 MPS 输入文件路径 |
| `--params` | `''`（空） | 求解器参数字符串（文本格式，原样传给求解器） |
| `--solver` | `sat` | 求解模型所用的求解器类型（如 `sat` 等 `model_builder.ModelSolver` 支持的名称） |

默认行为：不带参数运行时 `--input` 为空，`import_from_mps_file('')` 会失败，程序打印 `Cannot import MPS file: ''` 后退出——因此实际使用时必须通过 `--input` 提供 MPS 文件。

## 关键实现说明

- `ortools.linear_solver.python.model_builder`：新版 Python 建模 API（区别于老的 `pywraplp`），提供 `ModelBuilder`（构建/导入模型）与 `ModelSolver`（求解）。
- `ModelBuilder.import_from_mps_file(path)`：导入 MPS 文件；返回布尔值表示成功与否。
- `ModelSolver(name)`：按名称实例化后端求解器；`solver_is_supported()` 判断该名称是否受支持。
- `set_solver_specific_parameters(str)`：以字符串形式设置后端求解器的专有参数。
- `enable_output(True)`：开启求解器日志输出（求解过程、解的状态等信息会打印到控制台）。
- `solver.solve(model)`：执行求解（本例未显式读取状态码，结果通过日志呈现）。
- absl flags：`_INPUT`、`_PARAMS`、`_SOLVER` 三个命令行参数，入口为 `app.run(main)`。
