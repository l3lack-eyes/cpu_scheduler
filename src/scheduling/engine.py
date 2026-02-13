from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional, Tuple


@dataclass
class ProcState:
    pid: str
    arrival_time: int
    burst_time: int
    priority: Optional[int] = None

    remaining: int = field(init=False)
    first_start: Optional[int] = None
    completion_time: Optional[int] = None

    quantum_left: Optional[int] = None
    level: int = 0

    def __post_init__(self):
        self.remaining = int(self.burst_time)


@dataclass
class Segment:
    start: int
    end: int
    pid: str


def merge_segments(segments: List[Segment]) -> List[Segment]:
    if not segments:
        return []
    merged: List[Segment] = [segments[0]]
    for seg in segments[1:]:
        last = merged[-1]
        if seg.pid == last.pid and seg.start == last.end:
            last.end = seg.end
        else:
            merged.append(seg)
    return [s for s in merged if s.end > s.start]


class Policy:
    name: str
    preempt_on_arrival: bool = False

    def on_arrival(self, p: ProcState, now: int) -> None:  # pragma: no cover
        raise NotImplementedError

    def select(self, now: int, current: Optional[ProcState]) -> Optional[ProcState]:  # pragma: no cover
        raise NotImplementedError

    def max_continuous_run(self, p: ProcState, now: int) -> Optional[int]:
        return None

    def on_run(self, p: ProcState, ran_for: int, now: int) -> None:
        pass

    def on_timeslice_expired(self, p: ProcState, now: int) -> None:  # pragma: no cover
        raise NotImplementedError

    def put_back(self, p: ProcState, now: int) -> None:
        self.on_arrival(p, now)


def simulate(
    processes: List[ProcState],
    policy: Policy,
    context_switch_time: int,
) -> Tuple[List[Segment], List[ProcState]]:

    n = len(processes)
    if n == 0:
        return [], processes
    arrival_sorted = sorted(processes, key=lambda p: (p.arrival_time, p.pid))
    idx = 0
    time = 0
    done = 0
    current: Optional[ProcState] = None
    segments: List[Segment] = []
    last_run_pid: Optional[str] = None
    last_run_end: Optional[int] = None

    def next_arrival_time() -> Optional[int]:
        return arrival_sorted[idx].arrival_time if idx < n else None

    def push_arrivals(up_to: int) -> None:
        nonlocal idx
        while idx < n and arrival_sorted[idx].arrival_time <= up_to:
            p = arrival_sorted[idx]
            policy.on_arrival(p, p.arrival_time)
            idx += 1

    first_arrival = arrival_sorted[0].arrival_time
    if first_arrival > 0:
        segments.append(Segment(0, first_arrival, "IDLE"))
        time = first_arrival
        last_run_pid = None
        last_run_end = None

    while done < n:
        push_arrivals(time)

        selected = policy.select(time, current)
        if selected is None:
            na = next_arrival_time()
            if na is None:
                break
            if na > time:
                segments.append(Segment(time, na, "IDLE"))
                last_run_pid = None
                last_run_end = None
                time = na
            current = None
            continue
        if current is not None and selected.pid != current.pid:
            current = None

        if (
            context_switch_time > 0

            and last_run_pid is not None
            and last_run_pid != selected.pid
            and last_run_end == time

            and segments
            and segments[-1].pid not in ("IDLE", "CS")
        ):

            cs_start = time
            cs_end = time + context_switch_time
            segments.append(Segment(cs_start, cs_end, "CS"))
            time = cs_end
            push_arrivals(time)
            last_run_pid = None
            last_run_end = None

        if selected.first_start is None:
            selected.first_start = time

        max_run = policy.max_continuous_run(selected, time)
        if max_run is None:
            max_run = selected.remaining
        max_run = min(max_run, selected.remaining)
        stop_at_arrival = None
        if policy.preempt_on_arrival:
            na = next_arrival_time()
            if na is not None and na > time:
                stop_at_arrival = na
                max_run = min(max_run, na - time)

        if max_run <= 0:
            na = next_arrival_time()
            if na is None:
                break
            if na > time:
                segments.append(Segment(time, na, "IDLE"))
                last_run_pid = None
                last_run_end = None
                time = na
            current = None
            continue

        start = time
        end = time + max_run
        segments.append(Segment(start, end, selected.pid))
        last_run_pid = selected.pid
        last_run_end = end

        time = end
        selected.remaining -= max_run
        policy.on_run(selected, max_run, time)
        push_arrivals(time)

        if selected.remaining == 0:
            selected.completion_time = time
            done += 1
            current = None
            continue

        if policy.preempt_on_arrival and stop_at_arrival is not None and time == stop_at_arrival:
            current = selected
            continue

        policy.on_timeslice_expired(selected, time)
        current = None

    if len(segments) >= 2 and segments[-2].pid == "CS" and segments[-1].pid == "IDLE":
        cs = segments[-2]
        idle = segments[-1]
        segments[-2] = Segment(cs.start, idle.end, "IDLE")
        segments.pop()
    if segments and segments[-1].pid == "CS":
        segments.pop()

    return merge_segments(segments), processes