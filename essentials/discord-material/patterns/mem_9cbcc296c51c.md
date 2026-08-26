AGENTS.md / system-prompt philosophy (from mentor Tom, Discord 8/11/26): Don't over-restrict the agent with scope discipline — an overly restricted AGENTS.md blocks the agent from finishing real problems. High-risk drifts in AGENTS.md (despite sounding good on paper): "choose the simplest implementation", "grow the system in layers / never trade a working product for unfinished complexity", "make architectural decisions for the long term / no stopgaps", "study how established products solve the problem / adopt their patterns". These steer BEHAVIOR and over-constrain the model. Instead: STEER OUTCOMES, not behavior. Convert almost all of these patterns into a CI CHECK so you let the AI rampage and do what it's good at, then it steers itself to your idealized graph of implementation. Do checks at the END so you can iterate faster and let the agent do its testing loop. Create a PR, gh watch the CI, resolve issues — a conclusive loop to round out the edges. Everything should be technically verifiable, even code taste. Small exceptions ok, but big overreaching ones affect the post-training portion of the agent.

<!-- MEMORY_FIELDS
{
  "version": 1
}
-->