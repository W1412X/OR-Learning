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
"""从 MPS 文件加载模型并用 model_builder API 求解。"""

from absl import app
from absl import flags
from ortools.linear_solver.python import model_builder

FLAGS = flags.FLAGS

# 命令行参数：要加载并求解的输入 MPS 文件路径。
_INPUT = flags.DEFINE_string('input', '', 'Input file to load and solve.')
# 命令行参数：以字符串形式给出的求解器参数。
_PARAMS = flags.DEFINE_string('params', '', 'Solver parameters in string format.')
# 命令行参数：求解模型所用的求解器类型（默认为 'sat'）。
_SOLVER = flags.DEFINE_string('solver', 'sat', 'Solver type to solve the model with.')


def main(_):
    # 创建模型构建器（模型将完全来自 MPS 文件，而非手工建模）。
    model = model_builder.ModelBuilder()

    # 从 MPS 文件加载模型。
    if not model.import_from_mps_file(_INPUT.value):
        print(f'Cannot import MPS file: \'{_INPUT.value}\'')
        return

    # 按名称创建求解器（如 'sat' 等）。
    solver = model_builder.ModelSolver(_SOLVER.value)
    if not solver.solver_is_supported():
        print(f'Cannot create solver with name \'{_SOLVER.value}\'')
        return

    # 设置求解器专有参数（若命令行提供了 --params）。
    if _PARAMS.value:
        solver.set_solver_specific_parameters(_PARAMS.value)

    # 开启求解器日志输出。
    solver.enable_output(True)

    # 执行求解。
    solver.solve(model)


if __name__ == '__main__':
    app.run(main)
