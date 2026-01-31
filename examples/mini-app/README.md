# Mini App (Intentional Vulnerabilities)

This tiny app is intentionally vulnerable to make demos deterministic.
Do not deploy this code.

Targets for the demo:
- SQL injection in `get_user`.
- Command injection in `run_report`.
- SSRF risk in `fetch_profile`.
- Insecure deserialisation in `load_session`.
