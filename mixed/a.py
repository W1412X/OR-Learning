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
    solver.Minimize(200 * y1 + 300 * y2 + 150 * y3 + 10 * x1 + 15 * x2 + 12 * x3)

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
