from __future__ import annotations

from tis.planner.models import Recommendation


def pareto_frontier(recommendations: list[Recommendation]) -> list[Recommendation]:
    frontier: list[Recommendation] = []
    for candidate in recommendations:
        dominated = False
        for other in recommendations:
            if other is candidate:
                continue
            if (
                other.metrics.cost_usd <= candidate.metrics.cost_usd
                and other.metrics.time_hours <= candidate.metrics.time_hours
                and (
                    other.metrics.cost_usd < candidate.metrics.cost_usd
                    or other.metrics.time_hours < candidate.metrics.time_hours
                )
            ):
                dominated = True
                break
        if not dominated:
            frontier.append(candidate)
    return frontier
