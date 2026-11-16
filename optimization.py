from simulation import *
from policy_evaluation import *
from scipy.optimize import differential_evolution
import numpy as np
import matplotlib.pyplot as plt

class TestPolicy:
    def __init__(self, x):
        self.x = x
        self.prev_target = None
        self.pid = PID(Kp=x[1], Ki=0.0, Kd=0.0)

    def invoke(self, s):
        n_new = math.ceil(len(s.queue) / self.x[0])
        if self.prev_target is None:
            self.prev_target = s.desired_capacity
        n_current = self.prev_target
        self.prev_target = clamp(n_current + self.pid(n_new - n_current), s.min_workers, s.max_workers)
        s.desired_capacity = clamp(round(self.prev_target), s.min_workers, s.max_workers)

def score(report):
    return (1.0-report.utilization)/(1.0-0.8) + report.avg_wait_time/60.0

def generate_dataset():
    result = []
    for profile_gen in (generate_profile_1, generate_profile_2):
        for i in range(5):
            result.append(profile_gen(seed=8635+i))
    return result

def f(x, profiles=generate_dataset()):
    results = []
    for profile in profiles:
        policy = TestPolicy(x)
        report = run_simulation(policy, profile)
        results.append(score(report))
    return sum(results) / len(results)

bounds = [(0.5, 15.0), (0.0, 1.0)]
res = differential_evolution(f, bounds=bounds, tol=0.1, polish=False, maxiter=100, seed=6071, popsize=10)
print(res)

policy = TestPolicy(res.x)
load_profile1 = generate_profile_1()
report1 = run_simulation(policy, load_profile1)

policy = TestPolicy(res.x)
load_profile2 = generate_profile_2()
report2 = run_simulation(policy, load_profile2)

print(report1.utilization, report1.avg_wait_time)
print(report2.utilization, report2.avg_wait_time)
fig, ax = plt.subplot_mosaic(
[
    ['1'],
    ['2'],
])
make_plot(ax['1'], load_profile1, report1)
make_plot(ax['2'], load_profile2, report2)
plt.show()