from simulation import *
from dataclasses import dataclass
from unittest import TestCase, main

@dataclass
class TestEvent:
    t: int

class TestTimeline(TestCase):
    def test_add(self):
        t = Timeline()
        self.assertEqual(t.data, [END])
        t.add(TestEvent(7))
        self.assertEqual(t.data, [TestEvent(7), END])
        t.add(TestEvent(9))
        self.assertEqual(t.data, [TestEvent(7), TestEvent(9), END])
        t.add(TestEvent(5))
        self.assertEqual(t.data, [TestEvent(5), TestEvent(7), TestEvent(9), END])
        t.add(TestEvent(8))
        self.assertEqual(t.data, [TestEvent(5), TestEvent(7), TestEvent(8), TestEvent(9), END])
        t.add(TestEvent(6))
        self.assertEqual(t.data, [TestEvent(5), TestEvent(6), TestEvent(7), TestEvent(8), TestEvent(9), END])

class AutoscalerStab:
    def peek(self):
        return END.t

    def step(self):
        return

class TestAdjustCapacity(TestCase):
    def test(self):
        s = State(
            autoscaling=AutoscalerStab(),
            put_task=Timeline(),
            task_done=Timeline(),
            worker_ready=Timeline(),
            worker_shutdown=Timeline(),
            rng=random.Random(123),
            min_workers=0,
            max_workers=10,
            desired_capacity=0,
            idle_workers=0,
            busy_workers=0,
            launching_workers=0,
            shutting_down_workers=0)

        s.desired_capacity = 2
        adjust_capacity(s, 8)
        self.assertEqual(s.launching_workers, 2)
        self.assertEqual(s.idle_workers, 0)
        self.assertEqual(s.worker_ready.data, [WorkerReadyEvent(99), WorkerReadyEvent(102), END])

        adjust_capacity(s, 15)
        self.assertEqual(s.launching_workers, 2)
        self.assertEqual(s.idle_workers, 0)
        self.assertEqual(s.worker_ready.data, [WorkerReadyEvent(99), WorkerReadyEvent(102), END])

        next_event(s)
        self.assertEqual(s.launching_workers, 1)
        self.assertEqual(s.idle_workers, 1)

        next_event(s)
        self.assertEqual(s.launching_workers, 0)
        self.assertEqual(s.idle_workers, 2)

    def test_2(self):
        s = State(
            autoscaling=AutoscalerStab(),
            put_task=Timeline(),
            task_done=Timeline(),
            worker_ready=Timeline(),
            worker_shutdown=Timeline(),
            rng=random.Random(123),
            min_workers=0,
            max_workers=10,
            desired_capacity=0,
            idle_workers=2,
            busy_workers=0,
            launching_workers=0,
            shutting_down_workers=0)

        s.desired_capacity = 1
        adjust_capacity(s, 8)
        self.assertEqual(s.shutting_down_workers, 1)
        self.assertEqual(s.idle_workers, 1)
        self.assertEqual(s.worker_shutdown.data, [WorkerShutdownEvent(102), END])

        next_event(s)
        self.assertEqual(s.shutting_down_workers, 0)
        self.assertEqual(s.idle_workers, 1)

        adjust_capacity(s, 8)
        self.assertEqual(s.shutting_down_workers, 0)
        self.assertEqual(s.idle_workers, 1)

    def test_3(self):
        s = State(
            autoscaling=AutoscalerStab(),
            put_task=Timeline(),
            task_done=Timeline(),
            worker_ready=Timeline(),
            worker_shutdown=Timeline(),
            rng=random.Random(123),
            min_workers=0,
            max_workers=10,
            desired_capacity=0,
            idle_workers=0,
            busy_workers=0,
            launching_workers=0,
            shutting_down_workers=0)

        s.desired_capacity = 1
        adjust_capacity(s, 3)
        self.assertEqual(s.launching_workers, 1)
        self.assertEqual(s.worker_ready.data, [WorkerReadyEvent(97), END])

        s.desired_capacity = 2
        adjust_capacity(s, 5)
        self.assertEqual(s.launching_workers, 2)
        self.assertEqual(s.worker_ready.data, [WorkerReadyEvent(96), WorkerReadyEvent(97), END])

        next_event(s)
        self.assertEqual(s.launching_workers, 1)
        self.assertEqual(s.idle_workers, 1)

        next_event(s)
        self.assertEqual(s.launching_workers, 0)
        self.assertEqual(s.idle_workers, 2)

        s.desired_capacity = 3
        adjust_capacity(s, 103)
        self.assertEqual(s.launching_workers, 1)
        self.assertEqual(s.idle_workers, 2)
        self.assertEqual(s.worker_ready.data, [WorkerReadyEvent(96), WorkerReadyEvent(97), WorkerReadyEvent(189), END])

        s.desired_capacity = 0
        adjust_capacity(s, 151)
        self.assertEqual(s.launching_workers, 1)
        self.assertEqual(s.idle_workers, 0)
        self.assertEqual(s.shutting_down_workers, 2)
        self.assertEqual(s.worker_shutdown.data, [WorkerShutdownEvent(243), WorkerShutdownEvent(244), END])

        next_event(s)
        self.assertEqual(s.launching_workers, 0)
        self.assertEqual(s.idle_workers, 0)
        self.assertEqual(s.shutting_down_workers, 3)
        self.assertEqual(s.worker_shutdown.data, [WorkerShutdownEvent(243), WorkerShutdownEvent(244), WorkerShutdownEvent(277), END])

if __name__ == '__main__':
    main()