# Decisions

- Original Python standard-library implementation: the learning goal is explicit cache state and deterministic time, not a full recursive resolver. dnspython/Unbound inspected but not copied, installed or executed.
- Strict normalized schema: no guessing NODATA from an empty answer, no deriving completed failure from one response. IN and supported types are explicit bounds.
- One combined cache map with disjoint categories: a total cap and expiry sweep precede conflict handling. A refresh preserves unrelated AAAA NODATA/failure.
- Exact simulated milliseconds: no sleep or wall-clock dependence. TTL-zero/no-SOA events leave reusable state unchanged under this documented model policy.
- CNAME singular target and terminal-only denials/failures: aliases and target entries have independent lifetimes; cycles/depth produce model errors, not fabricated absence.
- Stdout-only CLI: removes output-file alias/overwrite logic. Semantic output is assembled atomically, but physical delivery/shell redirects cannot be transactional.
- No standalone repository initialization/publication in this stage. The approved work is local tool/tests/docs; hosted CodeQL/Bandit and branch protections have not been configured or run. Any owned repository creation must apply Jake's repository security baseline.
