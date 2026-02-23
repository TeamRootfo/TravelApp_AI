---
trigger: manual
---

Python Best Practices Enforcement

Before commit or completion:

1) Code Standards
- Follow PEP8
- Use type hints everywhere possible
- Avoid using Any unless necessary
- Use dataclasses or pydantic models instead of raw dicts for structured data
- Avoid global mutable state

2) Error Handling
- No bare except:
- Raise specific exceptions
- Use context managers for file/db handling

3) Structure
- Separate business logic from I/O
- No large god-functions (>50 lines without strong reason)
- No deep nesting (max 3 levels ideally)

4) Security
- Validate inputs
- Avoid shell=True in subprocess
- No unsafe eval/exec

5) Performance
- Avoid unnecessary loops
- Prefer comprehensions when readable
- Avoid repeated DB/API calls inside loops

6) Testing
- Ensure new logic has at least 1 test
- Avoid brittle time-dependent tests

Always output:
- Best Practice Violations
- Suggested Refactors
- Risk Level (Low/Medium/High)
- Production Readiness Verdict