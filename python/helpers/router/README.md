# Deterministic Router v2

> Policy-driven multi-intent routing without LLM judgment.

## Overview

The Deterministic Router replaces non-deterministic LLM-based routing with a pure code-driven policy system. Same input always produces same output.

## Features

- **Deterministic**: SHA256-based route_id/input_hash, no randomness
- **Multi-Intent**: Detects multiple domains (finance + legal + sales)
- **Board-Level Triggers**: Strategic requests get special handling
- **Anti-Injection**: Blocks override/disable attempts
- **Contract-Safe**: PROCEED always has at least one intent

## Quick Start

```python
from python.helpers.router import decide_route, RouteVerdict, IntentName

decision = decide_route("Analyse financière du deal M&A")

if decision.verdict == RouteVerdict.PROCEED:
    for intent in decision.intents:
        print(f"  {intent.name.value}: {intent.score:.2f}")
    
    if decision.is_board_level:
        print("  → Board-level request!")
```

## Feature Flag

Enable the router by setting the environment variable:

```bash
# Enable deterministic router
export DETERMINISTIC_ROUTER_V2=1

# Or in .env file
DETERMINISTIC_ROUTER_V2=1
```

When enabled:

- Router runs in parallel with existing LLM-based routing
- Decisions are logged for audit
- Divergences between LLM choice and router decision are flagged
- **No behavioral change** to existing flow (audit-only mode)

When disabled (default):

- Router module is not invoked
- Existing LLM-based routing unchanged

## Architecture

```text
python/helpers/router/
├── __init__.py           # Exports + feature flag
├── routing_contract.py   # Strict schemas (RouteDecision, AgentResult)
├── policy.py             # Weighted keywords + board-level triggers
├── router.py             # decide_route() pure function
├── judge.py              # Pre-consensus contradiction detection
└── README.md             # This file
```

## Key Components

### RouteDecision

```python
@dataclass
class RouteDecision:
    verdict: RouteVerdict           # PROCEED | NEEDS_CLARIFICATION | REFUSE
    intents: List[RouteIntent]      # Detected intents with scores
    confidence: float               # 0.0 - 1.0
    is_board_level: bool            # Strategic request?
    requires_contradictor: bool     # Needs second opinion?
    injection_blocked: bool         # Override attempt detected?
    route_id: str                   # Stable hash for tracing
    input_hash: str                 # Stable input fingerprint
```

### Intent Policy

Each intent has:

- **Keywords**: Weighted terms with word boundaries
- **Blockers**: Terms that prevent this intent
- **Threshold**: Minimum score to activate
- **Critical**: If True, cannot be skipped when matched

### Board-Level Triggers

Strategic keywords that activate board-level mode:

- M&A: `acquisition d'entreprise`, `buyout`, `takeover`, `m&a`, `lbo`, `ipo`
- Strategic: `stratégie`, `comex`, `direction générale`
- Fundraising: `levée de fonds`, `série A`

**Note**: Generic `acquisition` was removed to prevent marketing false positives.

## Rollback Procedure

### Immediate Rollback (No Code Change)

Simply disable the feature flag:

```bash
# Disable deterministic router
unset DETERMINISTIC_ROUTER_V2
# or
export DETERMINISTIC_ROUTER_V2=0
```

The existing LLM-based routing continues to work normally.

### Full Rollback (Remove Code)

If you need to completely remove the router module:

```bash
# 1. Disable feature flag first
export DETERMINISTIC_ROUTER_V2=0

# 2. Verify no impact
python -m pytest tests/test_router.py -v

# 3. Remove integration from call_subordinate.py
git diff python/tools/call_subordinate.py  # Review changes
git checkout python/tools/call_subordinate.py  # Revert

# 4. Optionally remove router module
rm -rf python/helpers/router/
rm tests/test_router*.py tests/test_judge.py tests/test_policy*.py tests/test_injection*.py

# 5. Commit
git add -A && git commit -m "revert: Remove deterministic router"
```

### Partial Rollback (Keep Audit, Disable Enforcement)

Edit `python/helpers/router/__init__.py`:

```python
def is_deterministic_router_enabled() -> bool:
    # Force disable
    return False
```

## Testing

```bash
# Run all router tests
python -m pytest tests/test_router*.py tests/test_judge.py -v

# Run specific test categories
python -m pytest tests/test_router_determinism.py -v      # Determinism
python -m pytest tests/test_router_contract_safety.py -v  # Contract
python -m pytest tests/test_policy_board_level*.py -v     # Board-level
python -m pytest tests/test_injection*.py -v               # Injection
```

## Policy Version

Current: **1.1.0**

Changes in 1.1.0:

- Fixed acquisition collision (marketing vs M&A)
- Finance→Legal rule now requires board-level
- Injection patterns reduced to override-only

## Observability

When enabled, the router logs:

```json
[ROUTER_V2] a1b2c3d4 | Verdict: proceed | Intents: ['finance', 'legal_safe'] | BoardLevel: True | LLM profile: finance
[ROUTER_V2_AUDIT] correlation-id | DIVERGENCE: LLM chose 'finance', Router detected ['finance', 'legal_safe']
```

Log levels:

- `INFO`: Normal routing decisions
- `WARNING`: Divergences, injection attempts
- `ERROR`: Router failures (falls back to existing behavior)

## Known Limitations

1. **RESEARCHER is_critical=True**: May cause over-blocking for research queries. TODO P1.
2. **Numeric contradiction detection**: Judge step has basic numeric extraction. TODO P1.
3. **No enforcement mode yet**: Router runs in audit-only mode. Full enforcement requires Step 7.

## Contact

- Module owner: KOREV Engineering
- Policy updates: Update `policy.py` and bump `POLICY_VERSION`
