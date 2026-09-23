from ortools.linear_solver import pywraplp  
def solve():
    #1. 创建求解器（使用GLOP线性规划求解器）
    solver = pywraplp.Solver.CreateSolver('GLOP')
    x1=solver.NumVar(0,solver.infinity(),'flour_from_a')
    x2=solver.NumVar(0,solver.infinity(),'flour_from_b')
    solver.Add(x1+x2<=100)
    solver.Add(x1<=60)
    solver.Add(x2<=80)
    solver.Add(50*x1+30*x2<=4000)
    solver.Add(-x1<=-30)
    solver.Add(-x2<=-20)
    solver.Minimize(50*x1+30*x2)
    status=solver.Solve()
    print(f"解状态:{status}")
    print(f"x1={x1.solution_value()},x2={x2.solution_value()}")
    print(f"最小采购成本:{50*x1.solution_value()+30*x2.solution_value()}")
if __name__ == '__main__':
    solve()