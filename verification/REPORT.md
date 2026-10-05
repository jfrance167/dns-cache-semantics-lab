# Local verification — October 5, 2026

Windows, CPython 3.13.7. Approved stages 2–4 complete. Scope: original offline application, strict loader/schema, transition engine, JSON/text renderers, CLI, fictional scenario, tests and portfolio docs. No upstream resolver installed or executed.

| Check | Observed result |
|---|---|
| `python -m unittest discover -s tests -v` | 21 tests passed; final normal.log |
| `python -O -m unittest discover -s tests -v` | 21 passed; CLI children also use -O; optimized.log |
| `python -m compileall -q cache_lab.py tests` | exit 0 |
| Bandit 1.9.4, application and tests | exit 0, zero findings; bandit.json |
| Fictional demo, JSON and text | exit 0; demo.json and demo.text |
| Network prohibition check | replay succeeds with socket construction and getaddrinfo patched to fail |
| Deterministic output | repeated replay serialization matched in test |
| Mutated expiry `>` → `>=` | rejected: 4 failures, 1 error; mutation-expiry.log |
| Mutated A refresh to erase all owner entries | rejected: 2 failures; mutation-cross-type.log |
| Mutation restoration | exact original bytes restored; final suite rerun successfully |

Material semantics tested: exact/zero expiry and refresh, cross-type denials/failures, negative SOA lifetime in both directions, no-SOA preservation, independent aliases/terminal denial/recovery, cycles/eight-hop boundary, expired conflicts, shared capacity, source fictional ranges, DNS name total/label length and canonical duplicates, JSON nesting/numbers/control characters/duplicate keys, optimized execution and CLI no-partial-output errors. Expected outcomes are manually specified; mutation logs validate two key checks can fail.

Receipt source SHA-256: `f4d1f56b7688e748c5495a39f134e4515414ffa9d807c4796c56b76479c9b996`. See receipt.json for exact final exit codes and runtime. Full logs retained locally, ignored for a future Git repository. The earlier top-level verification-bandit.json is a separate initial passing scan; final evidence is this directory.

Initial verification found a test fixture miscalculation: the claimed 254-character DNS name was actually 256; fixed fixture to 254 and confirmed rejection at 255. Sandbox also denied Python's temporary fixture directory; approved execution with normal temporary-file access passed. No application exception was suppressed to make these checks pass.

## ECC self-review

Applied installed ecc-code-review pinned reviewer checklist to actual application source, loader/schema/clock trust boundaries, cache callers, CLI, tests, demo and docs after mutation restoration. Reviewed correctness, input handling, resource bounds, information inference, data-loss/error paths, dependencies and maintenance. No unresolved confirmed application defect found. This is implementing-agent self-review, not independent review or security certification.

Two narrow test-only Bandit exceptions: B404 for subprocess import and B603 for fixed installed interpreter/local CLI with generated inert JSON. No shell, third-party execution or arbitrary fixture command. Application has neither subprocess nor network calls. Python assertions are not used for application validation.

Limitations: Python 3.11/3.12 and Linux were not executed; hosted CI/CodeQL, standalone Git history and dedicated secret scanner were not run. No repository initialization, publication, workflow claims or live resolver/DNSSEC validation. Review of authored files found no credentials/private traffic; this is not a dedicated secret-scanning result. Stdout serialization is logically atomic for semantic errors; I/O delivery is not transactional.

Original Zig scanner Linux live SYN verification remains NOT RUN due to unavailable local runtime. This offline project neither resolves nor bypasses that blocker.
