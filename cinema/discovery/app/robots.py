"""A small robots.txt check. The live service uses the Archive search API, not a crawler."""

from __future__ import annotations


def robots_allows(robots_txt: str, path: str, user_agent: str = "SospanaCinemaBot") -> bool:
    if robots_txt is None:
        return True
    agents: list[tuple[str, list[str]]] = []
    current_agents: list[str] = []
    rules: list[str] = []

    def flush() -> None:
        if current_agents:
            agents.append((",".join(current_agents), list(rules)))

    for raw in robots_txt.splitlines():
        line = raw.split("#", 1)[0].strip()
        if not line or ":" not in line:
            continue
        key, value = [part.strip() for part in line.split(":", 1)]
        lowered = key.lower()
        if lowered == "user-agent":
            if rules:
                flush()
                current_agents = []
                rules.clear()
            current_agents.append(value.lower())
        elif lowered == "disallow" and current_agents:
            rules.append(value)
    flush()
    applicable = [rule for agent, rule in agents if agent == "*" or user_agent.lower() in agent.split(",")]
    if not applicable and agents:
        applicable = [rule for agent, rule in agents if "*" in agent.split(",")]
    for group in applicable:
        for rule in group:
            if rule and path.startswith(rule):
                return False
    return True
