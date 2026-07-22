"""Narrative and compliance agents.

Neither agent produces a number. They receive computed metrics as fact and
explain them; the compliance agent additionally checks that the narrative
contains no figure it wasn't given.
"""

from .narrative import Narrative, rule_based_narrative

__all__ = ["Narrative", "rule_based_narrative"]
