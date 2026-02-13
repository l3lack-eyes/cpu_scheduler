from __future__ import annotations

import heapq
from collections import deque
from typing import Deque, List, Optional, Tuple

from scheduling.engine import Policy, ProcState

def _key_arrival_pid(p: ProcState) -> Tuple[int, str]:
    return (int(p.arrival_time), str(p.pid))


def _ready_since(p: ProcState) -> int:
    return int(getattr(p, "ready_since", p.arrival_time))


def _mark_ready(p: ProcState, now: int) -> None:
    try:
        setattr(p, "ready_since", int(now))
    except Exception:
        pass



class FCFS(Policy):
    name = "FCFS"
    preempt_on_arrival = False

    def __init__(self):
        self.q: Deque[ProcState] = deque()

    def on_arrival(self, p: ProcState, now: int) -> None:
        _mark_ready(p, now)
        self.q.append(p)

    def put_back(self, p: ProcState, now: int) -> None:
        _mark_ready(p, now)
        self.q.append(p)

    def select(self, now: int, current: Optional[ProcState]) -> Optional[ProcState]:
        return current if current is not None else (self.q.popleft() if self.q else None)

    def max_continuous_run(self, p: ProcState, now: int) -> Optional[int]:
        return int(p.remaining)

    def on_timeslice_expired(self, p: ProcState, now: int) -> None:
        raise RuntimeError("FCFS has no time slice")



class SJF(Policy):

    name = "SJF"
    preempt_on_arrival = False

    def __init__(self):
        self.h: List[Tuple[int, int, str, ProcState]] = []

    def on_arrival(self, p: ProcState, now: int) -> None:
        _mark_ready(p, now)
        heapq.heappush(self.h, (int(p.remaining), int(p.arrival_time), str(p.pid), p))

    def put_back(self, p: ProcState, now: int) -> None:
        _mark_ready(p, now)
        heapq.heappush(self.h, (int(p.remaining), int(p.arrival_time), str(p.pid), p))

    def select(self, now: int, current: Optional[ProcState]) -> Optional[ProcState]:
        return current if current is not None else (heapq.heappop(self.h)[-1] if self.h else None)

    def max_continuous_run(self, p: ProcState, now: int) -> Optional[int]:
        return int(p.remaining)

    def on_timeslice_expired(self, p: ProcState, now: int) -> None:
        raise RuntimeError("SJF has no time slice")

class HRRN(Policy):

    name = "HRRN"
    preempt_on_arrival = False

    def __init__(self):
        self.ready: List[ProcState] = []

    def on_arrival(self, p: ProcState, now: int) -> None:
        _mark_ready(p, now)
        self.ready.append(p)

    def put_back(self, p: ProcState, now: int) -> None:
        _mark_ready(p, now)
        self.ready.append(p)

    def select(self, now: int, current: Optional[ProcState]) -> Optional[ProcState]:
        if current is not None:
            return current
        if not self.ready:
            return None

        best_i = 0
        best_rr = -1.0
        for i, p in enumerate(self.ready):
            waiting = max(0, int(now) - _ready_since(p))
            service = max(1, int(p.remaining))
            rr = (waiting + service) / service
            if rr > best_rr:
                best_rr = rr
                best_i = i
            elif rr == best_rr:
                if _key_arrival_pid(p) < _key_arrival_pid(self.ready[best_i]):
                    best_i = i
        return self.ready.pop(best_i)

    def max_continuous_run(self, p: ProcState, now: int) -> Optional[int]:
        return int(p.remaining)

    def on_timeslice_expired(self, p: ProcState, now: int) -> None:
        raise RuntimeError("HRRN has no time slice")


class SRTF(Policy):
    name = "SRTF"
    preempt_on_arrival = True

    def __init__(self):
        self.h: List[Tuple[int, int, str, ProcState]] = []

    def on_arrival(self, p: ProcState, now: int) -> None:
        _mark_ready(p, now)
        heapq.heappush(self.h, (int(p.remaining), int(p.arrival_time), str(p.pid), p))

    def put_back(self, p: ProcState, now: int) -> None:
        _mark_ready(p, now)
        heapq.heappush(self.h, (int(p.remaining), int(p.arrival_time), str(p.pid), p))

    def select(self, now: int, current: Optional[ProcState]) -> Optional[ProcState]:
        if current is None:
            return heapq.heappop(self.h)[-1] if self.h else None
        if not self.h:
            return current

        best = self.h[0][-1]
        best_key = (int(best.remaining), int(best.arrival_time), str(best.pid))
        cur_key = (int(current.remaining), int(current.arrival_time), str(current.pid))

        if best_key < cur_key:
            heapq.heappush(self.h, (int(current.remaining), int(current.arrival_time), str(current.pid), current))
            return heapq.heappop(self.h)[-1]
        return current

    def max_continuous_run(self, p: ProcState, now: int) -> Optional[int]:
        return int(p.remaining)

    def on_timeslice_expired(self, p: ProcState, now: int) -> None:
        raise RuntimeError("SRTF does not use fixed time slices")

class RR(Policy):
    name = "RR"
    preempt_on_arrival = False

    def __init__(self, quantum: int):
        if int(quantum) <= 0:
            raise ValueError("time_slice must be > 0 for RR")
        self.quantum = int(quantum)
        self.q: Deque[ProcState] = deque()

    def on_arrival(self, p: ProcState, now: int) -> None:
        _mark_ready(p, now)
        self.q.append(p)

    def put_back(self, p: ProcState, now: int) -> None:
        _mark_ready(p, now)
        self.q.append(p)

    def select(self, now: int, current: Optional[ProcState]) -> Optional[ProcState]:
        if current is not None:
            return current
        return self.q.popleft() if self.q else None

    def max_continuous_run(self, p: ProcState, now: int) -> Optional[int]:
        return min(int(p.remaining), self.quantum)

    def on_timeslice_expired(self, p: ProcState, now: int) -> None:
        self.put_back(p, now)

class _QueueAlgo:
    def __init__(self, algo: str, quantum: Optional[int] = None):
        self.algo = (algo or "FCFS").strip().upper()
        self.quantum = int(quantum) if quantum is not None else None

        if self.algo == "RR":
            if self.quantum is None or self.quantum <= 0:
                raise ValueError("RR queue requires time_slice > 0")
            self.q: Deque[ProcState] = deque()
        elif self.algo == "FCFS":
            self.q = deque()
        elif self.algo in {"SJF", "SPN"}:
            self.h: List[Tuple[int, int, str, ProcState]] = []
        elif self.algo == "HRRN":
            self.ready: List[ProcState] = []
        else:
            self.algo = "FCFS"
            self.q = deque()

    def add(self, p: ProcState, now: int) -> None:
        _mark_ready(p, now)
        if self.algo in {"RR", "FCFS"}:
            self.q.append(p)
        elif self.algo in {"SJF", "SPN"}:
            heapq.heappush(self.h, (int(p.remaining), int(p.arrival_time), str(p.pid), p))
        else:
            self.ready.append(p)

    def empty(self) -> bool:
        if self.algo in {"RR", "FCFS"}:
            return not self.q
        if self.algo in {"SJF", "SPN"}:
            return not self.h
        return not self.ready

    def pick(self, now: int) -> Optional[ProcState]:
        if self.empty():
            return None

        if self.algo in {"RR", "FCFS"}:
            return self.q.popleft()

        if self.algo in {"SJF", "SPN"}:
            return heapq.heappop(self.h)[-1]

        best_i = 0
        best_rr = -1.0
        for i, p in enumerate(self.ready):
            waiting = max(0, int(now) - _ready_since(p))
            service = max(1, int(p.remaining))
            rr = (waiting + service) / service
            if rr > best_rr:
                best_rr = rr
                best_i = i
            elif rr == best_rr:
                if _key_arrival_pid(p) < _key_arrival_pid(self.ready[best_i]):
                    best_i = i
        return self.ready.pop(best_i)

    def max_run(self, p: ProcState) -> int:
        if self.algo == "RR":
            return min(int(p.remaining), int(self.quantum))
        return int(p.remaining)

    def on_run(self, p: ProcState, ran_for: int) -> None:
        return

    def on_timeslice_expired(self, p: ProcState, now: int) -> None:
        self.add(p, now)



class MLQ(Policy):
    name = "MLQ"
    preempt_on_arrival = False

    def __init__(self, queues: List[dict], priority_mapping: str = "1-4"):
        if len(queues) != 4:
            raise ValueError("MLQ requires exactly 4 queues")

        self.queues: List[_QueueAlgo] = []
        for cfg in list(queues):
            algo = cfg.get("algorithm") or cfg.get("algo") or "FCFS"
            quantum = cfg.get("time_slice") or cfg.get("timeSlice")
            self.queues.append(_QueueAlgo(algo, quantum=quantum))

        self.priority_mapping = (priority_mapping or "1-4").strip()

    def _map_priority(self, priority: Optional[int]) -> int:
        if priority is None:
            return 3
        p = int(priority)
        if self.priority_mapping == "0-3":
            return max(0, min(3, p))
        return max(0, min(3, p - 1))

    def on_arrival(self, p: ProcState, now: int) -> None:
        q = self._map_priority(getattr(p, "priority", None))
        p.level = q
        self.queues[q].add(p, now)

    def put_back(self, p: ProcState, now: int) -> None:
        q = max(0, min(3, int(getattr(p, "level", 3))))
        self.queues[q].add(p, now)

    def select(self, now: int, current: Optional[ProcState]) -> Optional[ProcState]:
        if current is not None and int(getattr(current, "level", 3)) == 3:
            return current

        if current is None:
            return self._pick_highest(now)

        cur_lvl = int(getattr(current, "level", 3))
        for q in range(0, cur_lvl):
            if not self.queues[q].empty():
                self.queues[cur_lvl].add(current, now)
                return self._pick_highest(now)

        return current

    def _pick_highest(self, now: int) -> Optional[ProcState]:
        for q in range(4):
            if not self.queues[q].empty():
                p = self.queues[q].pick(now)
                if p is not None:
                    p.level = q
                return p
        return None

    def max_continuous_run(self, p: ProcState, now: int) -> Optional[int]:
        return self.queues[int(p.level)].max_run(p)

    def on_run(self, p: ProcState, ran_for: int, now: int) -> None:
        self.queues[int(p.level)].on_run(p, ran_for)

    def on_timeslice_expired(self, p: ProcState, now: int) -> None:
        self.queues[int(p.level)].on_timeslice_expired(p, now)


class MLFQ(Policy):
    name = "MLFQ"
    preempt_on_arrival = False

    def __init__(self, queues: List[dict]):
        if len(queues) != 4:
            raise ValueError("MLFQ requires exactly 4 levels")

        self.levels: List[_QueueAlgo] = []
        self.demote_slices: List[Optional[int]] = [None, None, None, None]

        for i, cfg in enumerate(list(queues)):
            algo = cfg.get("algorithm") or cfg.get("algo") or "FCFS"
            ts = cfg.get("time_slice") or cfg.get("timeSlice")
            ts_int = int(ts) if ts is not None else None

            if i < 3:
                if ts_int is None or ts_int <= 0:
                    raise ValueError("MLFQ levels 0..2 require time_slice > 0")
                self.demote_slices[i] = ts_int

            self.levels.append(_QueueAlgo(algo, quantum=ts_int))

    def on_arrival(self, p: ProcState, now: int) -> None:
        p.level = 0
        p.quantum_left = 0
        self.levels[0].add(p, now)

    def put_back(self, p: ProcState, now: int) -> None:
        lvl = max(0, min(3, int(getattr(p, "level", 0))))
        self.levels[lvl].add(p, now)

    def select(self, now: int, current: Optional[ProcState]) -> Optional[ProcState]:
        if current is not None and int(getattr(current, "level", 3)) == 3:
            return current

        if current is None:
            return self._pick_highest(now)

        cur_lvl = int(getattr(current, "level", 0))
        for lvl in range(0, cur_lvl):
            if not self.levels[lvl].empty():
                self.levels[cur_lvl].add(current, now)
                return self._pick_highest(now)

        return current

    def _pick_highest(self, now: int) -> Optional[ProcState]:
        for lvl in range(4):
            if not self.levels[lvl].empty():
                p = self.levels[lvl].pick(now)
                if p is not None:
                    p.level = lvl
                    if lvl < 3 and (p.quantum_left is None or int(p.quantum_left) <= 0):
                        p.quantum_left = int(self.demote_slices[lvl])
                return p
        return None

    def max_continuous_run(self, p: ProcState, now: int) -> Optional[int]:
        lvl = int(getattr(p, "level", 0))
        if lvl == 3:
            return int(p.remaining)
        ql = int(self.demote_slices[lvl]) if (p.quantum_left is None or int(p.quantum_left) <= 0) else int(p.quantum_left)
        return min(int(p.remaining), ql)

    def on_run(self, p: ProcState, ran_for: int, now: int) -> None:
        lvl = int(getattr(p, "level", 0))
        self.levels[lvl].on_run(p, ran_for)

        if lvl < 3:
            if p.quantum_left is None:
                p.quantum_left = int(self.demote_slices[lvl])
            p.quantum_left = int(p.quantum_left) - int(ran_for)

    def on_timeslice_expired(self, p: ProcState, now: int) -> None:
        lvl = int(getattr(p, "level", 0))

        if lvl == 3:
            self.levels[3].on_timeslice_expired(p, now)
            return

        if p.quantum_left is None or int(p.quantum_left) <= 0:
            new_lvl = min(3, lvl + 1)
            p.level = new_lvl
            p.quantum_left = 0
            self.levels[new_lvl].add(p, now)
        else:
            self.levels[lvl].on_timeslice_expired(p, now)
