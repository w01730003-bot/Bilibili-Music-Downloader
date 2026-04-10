from __future__ import annotations

from dataclasses import dataclass
import random
import time
from typing import Dict, Iterable, Optional


INFINITY_METRIC = 16


@dataclass
class RouteEntry:
    destination: str
    next_hop: Optional[str]
    metric: int
    interface: str
    source_neighbor: str
    timeout_at: Optional[float]
    garbage_collect_at: Optional[float]
    hold_down_until: Optional[float]
    is_direct: bool = False

    def refresh_timers(self, now: float, timeout_seconds: int) -> None:
        if self.is_direct:
            self.timeout_at = None
            self.garbage_collect_at = None
            return
        self.timeout_at = now + timeout_seconds
        self.garbage_collect_at = None


class RIPRouter:
    """
    Reusable RIP update algorithm implementation
    (distance-vector + timers).
    """

    def __init__(
        self,
        router_id: str,
        neighbors: Dict[str, str],
        *,
        update_interval: int = 30,
        timeout_seconds: int = 180,
        garbage_collect_seconds: int = 120,
        split_horizon: bool = True,
        poison_reverse: bool = True,
        hold_down_enabled: bool = True,
        hold_down_seconds: int = 180,
        trigger_jitter_range: tuple[float, float] = (1.0, 5.0),
    ) -> None:
        self.router_id = router_id
        self.neighbors = neighbors  # neighbor_id -> outgoing interface
        self.update_interval = update_interval
        self.timeout_seconds = timeout_seconds
        self.garbage_collect_seconds = garbage_collect_seconds
        self.split_horizon = split_horizon
        self.poison_reverse = poison_reverse
        self.hold_down_enabled = hold_down_enabled
        self.hold_down_seconds = hold_down_seconds
        self.trigger_jitter_range = trigger_jitter_range

        now = time.time()
        self.next_periodic_update_at = now + self.update_interval
        self.trigger_update_at: Optional[float] = None
        self.routing_table: Dict[str, RouteEntry] = {}
        self._dirty_destinations: set[str] = set()

    def add_direct_route(self, destination: str, interface: str, metric: int = 0) -> None:
        self.routing_table[destination] = RouteEntry(
            destination=destination,
            next_hop=None,
            metric=self._clamp_metric(metric),
            interface=interface,
            source_neighbor=self.router_id,
            timeout_at=None,
            garbage_collect_at=None,
            hold_down_until=None,
            is_direct=True,
        )

    def receive_update(
        self,
        from_neighbor: str,
        routes: Dict[str, int],
        *,
        now: Optional[float] = None,
    ) -> bool:
        """
        Process one neighbor update and apply RIP route selection rules.
        Returns True if local table changed.
        """
        if from_neighbor not in self.neighbors:
            raise ValueError(f"Unknown neighbor: {from_neighbor}")

        now = time.time() if now is None else now
        changed = False
        in_if = self.neighbors[from_neighbor]

        for destination, neighbor_metric in routes.items():
            new_metric = self._clamp_metric(neighbor_metric + 1)
            current = self.routing_table.get(destination)

            if current is None:
                if new_metric < INFINITY_METRIC:
                    self.routing_table[destination] = RouteEntry(
                        destination=destination,
                        next_hop=from_neighbor,
                        metric=new_metric,
                        interface=in_if,
                        source_neighbor=from_neighbor,
                        timeout_at=now + self.timeout_seconds,
                        garbage_collect_at=None,
                        hold_down_until=None,
                        is_direct=False,
                    )
                    changed = True
                    self._dirty_destinations.add(destination)
                continue

            if current.is_direct:
                continue

            same_source = current.source_neighbor == from_neighbor

            if same_source:
                if current.metric != new_metric:
                    changed = True
                    self._dirty_destinations.add(destination)
                current.metric = new_metric
                current.next_hop = from_neighbor
                current.interface = in_if
                current.source_neighbor = from_neighbor
                current.hold_down_until = None if new_metric < INFINITY_METRIC else (
                    now + self.hold_down_seconds if self.hold_down_enabled else None
                )
                current.refresh_timers(now, self.timeout_seconds)
                if new_metric >= INFINITY_METRIC:
                    current.garbage_collect_at = now + self.garbage_collect_seconds
                continue

            in_hold_down = (
                self.hold_down_enabled
                and current.hold_down_until is not None
                and now < current.hold_down_until
            )
            if in_hold_down:
                continue

            if new_metric < current.metric:
                current.metric = new_metric
                current.next_hop = from_neighbor
                current.interface = in_if
                current.source_neighbor = from_neighbor
                current.hold_down_until = None
                current.refresh_timers(now, self.timeout_seconds)
                changed = True
                self._dirty_destinations.add(destination)

        if changed:
            self._schedule_triggered_update(now)
        return changed

    def advance_timers(self, *, now: Optional[float] = None) -> bool:
        """
        Apply timeout and garbage-collection timers.
        Returns True if local table changed.
        """
        now = time.time() if now is None else now
        changed = False
        to_delete: list[str] = []

        for destination, route in self.routing_table.items():
            if route.is_direct:
                continue

            if route.metric < INFINITY_METRIC and route.timeout_at is not None and now >= route.timeout_at:
                route.metric = INFINITY_METRIC
                route.garbage_collect_at = now + self.garbage_collect_seconds
                route.hold_down_until = (
                    now + self.hold_down_seconds if self.hold_down_enabled else None
                )
                changed = True
                self._dirty_destinations.add(destination)
                continue

            if route.metric >= INFINITY_METRIC and route.garbage_collect_at is not None and now >= route.garbage_collect_at:
                to_delete.append(destination)

        for destination in to_delete:
            del self.routing_table[destination]
            changed = True

        if changed:
            self._schedule_triggered_update(now)
        return changed

    def get_periodic_updates(self, *, now: Optional[float] = None) -> Optional[Dict[str, Dict[str, int]]]:
        """
        Return full per-neighbor advertisements when periodic timer fires.
        Otherwise return None.
        """
        now = time.time() if now is None else now
        if now < self.next_periodic_update_at:
            return None

        self.next_periodic_update_at = now + self.update_interval
        return {n: self._build_advertisement_for_neighbor(n) for n in self.neighbors}

    def get_triggered_updates(self, *, now: Optional[float] = None) -> Optional[Dict[str, Dict[str, int]]]:
        """
        Return incremental per-neighbor advertisements when trigger timer fires.
        Otherwise return None.
        """
        now = time.time() if now is None else now
        if self.trigger_update_at is None or now < self.trigger_update_at:
            return None

        changed_destinations = tuple(self._dirty_destinations)
        self._dirty_destinations.clear()
        self.trigger_update_at = None

        return {
            n: self._build_advertisement_for_neighbor(n, only_destinations=changed_destinations)
            for n in self.neighbors
        }

    def _schedule_triggered_update(self, now: float) -> None:
        low, high = self.trigger_jitter_range
        delay = random.uniform(low, high)
        due = now + delay
        if self.trigger_update_at is None or due < self.trigger_update_at:
            self.trigger_update_at = due

    def _build_advertisement_for_neighbor(
        self,
        neighbor: str,
        *,
        only_destinations: Optional[Iterable[str]] = None,
    ) -> Dict[str, int]:
        if neighbor not in self.neighbors:
            raise ValueError(f"Unknown neighbor: {neighbor}")

        selected = (
            ((d, self.routing_table[d]) for d in only_destinations if d in self.routing_table)
            if only_destinations is not None
            else self.routing_table.items()
        )

        adv: Dict[str, int] = {}
        for destination, route in selected:
            metric = route.metric
            learned_from_neighbor = route.source_neighbor == neighbor

            if self.split_horizon and learned_from_neighbor:
                if self.poison_reverse:
                    metric = INFINITY_METRIC
                else:
                    continue

            adv[destination] = self._clamp_metric(metric)
        return adv

    @staticmethod
    def _clamp_metric(metric: int) -> int:
        return max(0, min(INFINITY_METRIC, metric))

    def snapshot(self) -> Dict[str, Dict[str, object]]:
        """
        Simplified routing table view for debugging/testing.
        """
        return {
            destination: {
                "next_hop": route.next_hop,
                "metric": route.metric,
                "interface": route.interface,
                "source_neighbor": route.source_neighbor,
                "is_direct": route.is_direct,
            }
            for destination, route in sorted(self.routing_table.items())
        }
