"""Processor layer — advanced middleware for the agent swarm.

Provides intelligent caching, bulk I/O, speculative planning,
routing, incremental learning, awareness projection, and
architecture self-documentation.
"""

from microgravity.agent.processors.cache import IntelligentCache
from microgravity.agent.processors.bulk_io import BulkIOProcessor
from microgravity.agent.processors.speculative_planner import SpeculativePlanner
from microgravity.agent.processors.routing import RoutingMapper
from microgravity.agent.processors.learner import IncrementalLearner
from microgravity.agent.processors.awareness import AwarenessProjector
from microgravity.agent.processors.arch_knowledge import ArchitectureKnowledgeBase

__all__ = [
    "IntelligentCache",
    "BulkIOProcessor",
    "SpeculativePlanner",
    "RoutingMapper",
    "IncrementalLearner",
    "AwarenessProjector",
    "ArchitectureKnowledgeBase",
]
