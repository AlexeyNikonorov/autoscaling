from dataclasses import dataclass, field
import random
import math
import numpy as np

@dataclass
class Task:
    duration: int
    time_added: int

@dataclass
class PutTaskEvent:
    t: int
    duration: int

@dataclass
class TaskDoneEvent:
    t: int

@dataclass
class WorkerReadyEvent:
    t: int

@dataclass
class WorkerShutdownEvent:
    t: int

@dataclass
class End:
    t: int = 999999
END = End()

class Timeline:
    def __init__(self, data=None):
        self.data = data+[END] if data is not None else [END]
        self.i = 0

    def add(self, item):
        n = len(self.data)
        while n > 0:
            if self.data[n-1].t <= item.t:
                self.data.insert(n, item)
                return
            n -= 1
        self.data = [item] + self.data

    def peek(self):
        return self.data[self.i]

    def step(self):
        self.i += 1

class AutoscalingTimeline:
    def __init__(self, t=0, poll=60):
        self.t = 0
        self.poll = poll

    def peek(self):
        return self.t

    def step(self):
        self.t += self.poll

@dataclass
class State:
    autoscaling: AutoscalingTimeline
    put_task: Timeline
    task_done: Timeline
    worker_ready: Timeline
    worker_shutdown: Timeline
    rng: random.Random
    min_workers: int = 0
    max_workers: int = 100
    desired_capacity: int = 0

    queue: list[Task] = field(default_factory=lambda: [])
    idle_workers: int = 0
    busy_workers: int = 0
    launching_workers: int = 0
    shutting_down_workers: int = 0
    wait_times: list[int] = field(default_factory=lambda: [])

def next_event(s):
    ts = (
        s.autoscaling.peek(),
        s.put_task.peek().t,
        s.task_done.peek().t,
        s.worker_ready.peek().t,
        s.worker_shutdown.peek().t,
    )
    t = min(ts)
    if t == ts[0]:
        on_autoscaling(s, s.autoscaling.peek())
        s.autoscaling.step()
    if t == ts[1]:
        on_put_task(s, s.put_task.peek())
        s.put_task.step()
    if t == ts[2]:
        on_task_done(s, s.task_done.peek())
        s.task_done.step()
    if t == ts[3]:
        on_worker_ready(s, s.worker_ready.peek())
        s.worker_ready.step()
    if t == ts[4]:
        on_worker_shutdown(s, s.worker_shutdown.peek())
        s.worker_shutdown.step()
    adjust_capacity(s, t)
    return t

class PID:
	def __init__(self, Kp, Ki, Kd):
		self.Kp, self.Ki, self.Kd = Kp, Ki, Kd
		self.I, self.e1 = 0.0, 0.0

	def __call__(self, e):
		D = e - self.e1
		self.e1 = e
		self.I = self.I + e
		return self.Kp*e + self.Ki*self.I + self.Kd*D

def clamp(x, x_min, x_max):
    if x_min <= x <= x_max:
        return x
    if x < x_min:
        return x_min
    return x_max

class AutoscalingPolicy:
    def __init__(self, Kp=1.0, Ki=0.0, Kd=0.0, tasks_per_worker=1.0):
        self.prev_target = None
        self.tasks_per_worker = tasks_per_worker
        self.pid = PID(Kp=Kp, Ki=Ki, Kd=Kd)

    def invoke(self, s):
        n_new = math.ceil(len(s.queue) / self.tasks_per_worker)
        if self.prev_target is None:
            self.prev_target = s.desired_capacity
        n_current = self.prev_target
        self.prev_target = clamp(n_current + self.pid(n_new - n_current), s.min_workers, s.max_workers)
        s.desired_capacity = clamp(round(self.prev_target), s.min_workers, s.max_workers)

def generate_launch_delays(n, rng):
    delays = [int(round(rng.gauss(90, 10))) for _ in range(n)]
    assert all(d >= 0 for d in delays)
    return delays

def generate_shutdown_delays(n, rng):
    delays = [int(round(rng.gauss(90, 10))) for _ in range(n)]
    assert all(d >= 0 for d in delays)
    return delays

policy = None
def set_policy(new_policy):
    global policy
    policy = new_policy

def on_autoscaling(s, t):
    policy.invoke(s)

def on_put_task(s, put_task):
    if s.idle_workers == 0:
        s.queue.append(
            Task(
                duration=put_task.duration,
                time_added=put_task.t))
        return
    s.wait_times.append(0)
    s.idle_workers -= 1
    s.busy_workers += 1
    s.task_done.add(
        TaskDoneEvent(
            t=put_task.t + put_task.duration))

def on_task_done(s, task_done):
    if not s.queue:
        s.busy_workers -= 1
        s.idle_workers += 1
        return
    task = s.queue.pop(0)
    assert task_done.t - task.time_added >= 0
    s.wait_times.append(task_done.t - task.time_added)
    s.task_done.add(
        TaskDoneEvent(
            t=task_done.t + task.duration))

def on_worker_ready(s, worker_ready):
    s.launching_workers -= 1
    if not s.queue:
        s.idle_workers += 1
        return
    task = s.queue.pop(0)
    assert worker_ready.t - task.time_added >= 0
    s.wait_times.append(worker_ready.t - task.time_added)
    s.task_done.add(
        TaskDoneEvent(
            t=worker_ready.t + task.duration))
    s.busy_workers += 1

def on_worker_shutdown(s, worker_shutdown):
    s.shutting_down_workers -= 1

def adjust_capacity(s, t):
    n = s.launching_workers + s.idle_workers + s.busy_workers
    if s.desired_capacity == n:
        return
    if s.desired_capacity > n:
        to_add = s.desired_capacity - n
        actual_add = min(to_add, s.max_workers - n - s.shutting_down_workers)
        s.launching_workers += actual_add
        launch_delays = generate_launch_delays(actual_add, s.rng)
        for d in launch_delays:
            s.worker_ready.add(
                WorkerReadyEvent(
                    t=t+d))
        return
    if s.desired_capacity < n:
        to_remove = n - s.desired_capacity
        actual_remove = min(to_remove, s.idle_workers)
        s.shutting_down_workers += actual_remove
        s.idle_workers -= actual_remove
        shutdown_delays = generate_shutdown_delays(actual_remove, s.rng)
        for d in shutdown_delays:
            s.worker_shutdown.add(
                WorkerShutdownEvent(
                    t=t+d))