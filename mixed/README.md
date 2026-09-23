## 混合整数规划
### 核心思想
在线性规划的基础上，要求**部分**决策变量只能取整数值，从而在连续可行域中引入离散决策，使模型能够同时处理"是否选择"和"选择多少"两类问题

### "混合整数"含义
- 当线性规划的**所有**决策变量都要求取值为整数时，该线性规划就变成了一个**整数规划** (Integer Programming, IP)，或者**纯整数规划** (Pure Integer Programming)
- 但当只有**一部分**决策变量要求取值为整数时，该线性规划就变为**混合整数规划** (Mixed Integer Programming, MIP)
- 混合整数规划的一般形式为：

$$
\min \quad m^T x + n^T y \tag{MIP}
$$

$$
\text{s.t.} \quad Ax + Cy \leq b
$$

$$
x \in \mathbb{R}^n, \quad y \in \mathbb{Z}^p
$$

其中 $x$ 为连续变量，$y$ 为整数变量

### 实际举例  
某公司有3个候选工厂，每个工厂若开设则需支付固定的开设成本。已知：

成本信息：

    工厂1的开设成本：200元
    工厂2的开设成本：300元
    工厂3的开设成本：150元

各工厂的单位生产成本和产能上限：

    工厂1：单位生产成本10元，最多生产80件
    工厂2：单位生产成本15元，最多生产60件
    工厂3：单位生产成本12元，最多生产70件

市场需求：

    总需求：至少需要100件产品

问题： 决定开设哪些工厂以及各工厂生产多少产品，在满足市场需求的前提下，使总成本（开设成本+生产成本）最小？

#### 题目分析
- 决策变量
  - $y_1, y_2, y_3$ 是否开设工厂1/2/3（0-1整数变量，1表示开设，0表示不开设）
  - $x_1, x_2, x_3$ 各工厂的产量（连续变量）
- 目标函数（最小化总成本）  
  - $
\min Z = (200y_1+300y_2+150y_3) + (10x_1+15x_2+12x_3)
$ 
- 约束条件：
  - 工厂1产能：$x_1 \leq 80y_1$  
  - 工厂2产能：$x_2 \leq 60y_2$  
  - 工厂3产能：$x_3 \leq 70y_3$  
  - 市场需求：$x_1+x_2+x_3 \geq 100$
  - 整数约束：$y_1,y_2,y_3 \in \{0,1\}$  
  - 非负约束：$x_1,x_2,x_3 \geq 0$  

> 注意：约束 $x_i \leq \text{Capacity}_i \cdot y_i$ 是MIP中的经典建模技巧——当 $y_i=0$（不开设）时，$x_i$ 被强制为0；当 $y_i=1$（开设）时，$x_i$ 可在产能范围内自由取值

#### 代码求解
```python
from ortools.linear_solver import pywraplp

def solve():
    # 1. 创建求解器（使用CBC混合整数规划求解器）
    solver = pywraplp.Solver.CreateSolver('CBC')

    # 2. 定义连续变量（各工厂产量）
    x1 = solver.NumVar(0, solver.infinity(), 'x1')
    x2 = solver.NumVar(0, solver.infinity(), 'x2')
    x3 = solver.NumVar(0, solver.infinity(), 'x3')

    # 3. 定义0-1整数变量（是否开设工厂）
    y1 = solver.IntVar(0, 1, 'y1')
    y2 = solver.IntVar(0, 1, 'y2')
    y3 = solver.IntVar(0, 1, 'y3')

    # 4. 添加约束
    # 产能约束：产量 <= 产能上限 * 是否开设
    solver.Add(x1 <= 80 * y1)
    solver.Add(x2 <= 60 * y2)
    solver.Add(x3 <= 70 * y3)
    # 市场需求约束
    solver.Add(x1 + x2 + x3 >= 100)

    # 5. 设置目标函数（最小化总成本 = 开设成本 + 生产成本）
    solver.Minimize(200*y1 + 300*y2 + 150*y3 + 10*x1 + 15*x2 + 12*x3)

    # 6. 求解
    status = solver.Solve()

    # 7. 输出结果
    print(f"解状态: {status}")
    print(f"工厂1: 开设={int(y1.solution_value())}, 产量={x1.solution_value()}")
    print(f"工厂2: 开设={int(y2.solution_value())}, 产量={x2.solution_value()}")
    print(f"工厂3: 开设={int(y3.solution_value())}, 产量={x3.solution_value()}")
    print(f"最小总成本: {solver.Objective().Value()}")

if __name__ == '__main__':
    solve()

```
