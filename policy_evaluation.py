import matplotlib.pyplot as plt
import random
import numpy as np
from dataclasses import dataclass, field

from simulation import *

def generate_profile_1(seed=123):
    rng = random.Random(seed)
    hours = 1
    n_samples = hours * 3000
    duration = hours * 3600
    timestamps = sorted([int(round(rng.random()*duration)) for _ in range(n_samples)])
    timestamps = [x - timestamps[0] for x in timestamps]
    return timestamps

def generate_profile_2(seed=123):
    rng = random.Random(seed)
    n_samples = 1000
    timestamp_variance = 600
    timestamps = sorted([int(round(rng.gauss(0, timestamp_variance))) for _ in range(n_samples)])
    timestamps = [x - timestamps[0] for x in timestamps]
    return timestamps

def area(x, y):
    assert len(x) == len(y)
    result = 0.0
    for i in range(1, len(x)):
        result += (x[i] - x[i-1]) * (y[i] + y[i-1])*0.5
    return result

@dataclass
class SimulationReport:
    timestamps: list[int] = field(default_factory=lambda: [])
    queue_size: list[int] = field(default_factory=lambda: [])
    workers: list[int] = field(default_factory=lambda: [])
    busy_workers: list[int] = field(default_factory=lambda: [])
    utilization: float = 0.0
    avg_wait_time: float = 0.0

def run_simulation(policy, load_profile):
    set_policy(policy)
    rng = random.Random(123)
    durations = [int(round(rng.gauss(40, 9))) for _ in range(len(load_profile))]
    assert all(x > 0 for x in durations)
    profile = [PutTaskEvent(t=x, duration=d) for x, d in zip(load_profile, durations)]
    
    s = State(
        autoscaling=AutoscalingTimeline(t=4, poll=60),
        put_task=Timeline(profile),
        task_done=Timeline(),
        worker_ready=Timeline(),
        worker_shutdown=Timeline(),
        rng=random.Random(123))

    simulation_duration = int(load_profile[-1] * 1.2)
    report = SimulationReport()
    t = 0
    while t < simulation_duration:
        t = next_event(s)
        report.timestamps.append(t)
        report.queue_size.append(len(s.queue))
        report.workers.append(s.idle_workers + s.busy_workers + s.launching_workers + s.shutting_down_workers)
        report.busy_workers.append(s.busy_workers)
    if len(s.wait_times) != len(load_profile):
        print('warning: not all tasks were processed')
    busy_time = area(report.timestamps, report.busy_workers)
    total_time = area(report.timestamps, report.workers)
    report.utilization = busy_time / total_time
    report.avg_wait_time = np.mean(s.wait_times)
    return report

def make_plot(ax, load_profile, report):
    simulation_duration = int(load_profile[-1]/60 * 1.2)
    bin_size = 1
    n_bins = simulation_duration // bin_size
    bins = [bin_size*i for i in range(n_bins)]
    ax.hist(np.array(load_profile)/60, bins=bins, alpha=0.3, color='green', label='Number of tasks received')
    ax.step(np.array(report.timestamps)/60, report.queue_size, lw=0.5, alpha=0.4, label='Number of tasks in queue')
    ax.step(np.array(report.timestamps)/60, report.workers, lw=0.8, alpha=1.0, label='Number of workers')
    ax.set_xlabel('Time, minutes', fontsize=7)
    for xtick in ax.get_xticklabels() + ax.get_yticklabels():
        xtick.set_fontsize(7)
    ax.annotate(
        text='Utilization: %.f%%\nAvg. wait time: %.f sec'%(report.utilization*100, report.avg_wait_time),
        textcoords='axes fraction',
        xytext=(0.98, 0.63),
        xy=(0.0, 0.0),
        ha='right',
        fontsize=7,
        alpha=0.9)

def make_dashboard(filename, **policy_kwargs):
    load_profile1 = generate_profile_1()
    policy = AutoscalingPolicy(**policy_kwargs)
    report1 = run_simulation(policy, load_profile1)
    
    load_profile2 = generate_profile_2()
    policy = AutoscalingPolicy(**policy_kwargs)
    report2 = run_simulation(policy, load_profile2)

    plt.style.use('ggplot')
    fig, ax = plt.subplot_mosaic(
    [
        ['1'],
        ['2'],
    ],
    figsize=(4, 4*1.6))
    make_plot(ax['1'], load_profile1, report1)
    make_plot(ax['2'], load_profile2, report2)
    ax['1'].set_ylim((0, 150))
    ax['2'].set_ylim((0, 80))
    ax['1'].legend(fontsize=7, loc='upper center')
    fig.savefig(filename, bbox_inches='tight')

if __name__ == '__main__':
    tasks_per_worker, Kp = 2.5, 1.0
    make_dashboard(f'plots/1_utilization_first.png', Kp=Kp, Ki=0.0, Kd=0.0, tasks_per_worker=tasks_per_worker)

    tasks_per_worker, Kp = 0.7, 1.0
    #tasks_per_worker, Kp = 1.0/1.994e+00, 1.530e-01
    make_dashboard(f'plots/2_wait_time_first.png', Kp=Kp, Ki=0.0, Kd=0.0, tasks_per_worker=tasks_per_worker)
