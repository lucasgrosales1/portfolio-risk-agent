"""portfolio-risk-agent — client-ready portfolio risk reporting.

Design rule that governs the whole package: **the LLM never produces a number.**
Every figure is computed in `pra.analytics` from real price data and handed to
the model as fact. The agents in `pra.agents` explain figures they were given
and nothing else.
"""

__version__ = "0.1.0"
