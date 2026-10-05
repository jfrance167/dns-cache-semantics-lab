# Offline DNS cache semantics lab — proposed contract

Status: stages 2–4 approved by coordinator at October 5 01:06 checkpoint under Jake's verified direct mandate. Addendum in ../.private/coordination/2026-10-05/SUCCESSORS.md reviewed before code. SCHEMA.md freezes the refined transitions and bounds. Reviewed 2026-10-05.

## Purpose and success

Teach why a repeat DNS question can reuse an answer, return a cached denial, be temporarily suppressed after failure, or require fresh information. Build an original Python standard-library CLI that replays fictional, normalized cache events and explains every decision. This is a teaching model of selected cache behavior, not a resolver or a claim of full DNS standards compliance.

The gap is distinct from the existing packet-forensics and Wireshark labs: those interpret DNS responses in traffic; this project explains cache identity and expiry over simulated elapsed time. The scanner remains a separate project with live Linux SYN verification pending.

## Proposed scope

- One JSON scenario in, deterministic JSON or plain-text timeline to stdout. No generated HTML, network access, live DNS, packet parsing, host cache inspection/flush, subprocesses, or system configuration.
- Python 3.11+; standard library only. Original implementation and MIT license with source attribution and AI-assistance disclosure. No borrowed resolver code.
- Absolute ASCII names under `example.` only, canonical lower case with trailing dot; IN class; A, AAAA and CNAME. Address data restricted to documentation ranges. No IDNA, wildcards, DNAME, delegations, DNSSEC, serve-stale, prefetch, ancestor NXDOMAIN cuts, or policy routing.
- Input at most 1 MiB, 256 events, 256 cache entries, 32 records per RRset, CNAME depth 8, simulated elapsed time at most 24 hours. Reject unsupported fields, duplicate JSON keys, invalid types (including bool as integer), non-finite numbers, contradictory records and decreasing time. Fail atomically without a partial timeline.
- Simulated integer milliseconds, nondecreasing timestamps, stable input order for equal timestamps. TTLs are integer seconds from 0 to 86400; expiry uses exact milliseconds. A query at expiry is a miss; TTL zero never becomes reusable. Limits are teaching-policy limits, not DNS protocol maxima.

## Model and semantics

Input events are explicit `store_rrset`, `store_negative`, `store_failure`, and `query`; source responses are already normalized. A miss produces `needs_information`, never fabricated NXDOMAIN or a real query. Positive entries identify owner/type/class; refresh replaces a complete RRset and restarts its lifetime. Each RRset has one shared TTL. Per-record unequal TTLs are rejected as unsupported input rather than silently repaired; authoritative/non-authoritative repair rules are outside this model. [RFC 2181 §5](https://www.rfc-editor.org/rfc/rfc2181.html#section-5).

NXDOMAIN is stored against terminal name/class; NODATA against terminal name/type/class. Negative lifetime uses the smaller of SOA TTL and SOA MINIMUM. Missing SOA causes a documented uncached event. SOA owner must be a label-boundary ancestor of the terminal name. NODATA is an explicit normalized category, not a numeric wire RCODE or inference from an empty answer alone. [RFC 2308 §§2–5](https://www.rfc-editor.org/rfc/rfc2308.html).

CNAME entries and terminal answers keep independent lifetimes. A query follows only currently cached aliases, reports each hop, and stops at a miss, terminal result, cycle or depth limit. Terminal NXDOMAIN does not assert the alias is absent. Direct CNAME queries return the alias RRset. [RFC 6604 §3](https://www.rfc-editor.org/rfc/rfc6604.html#section-3).

Failure events represent an explicitly completed synthetic resolution attempt with no useful response from any available server; one upstream SERVFAIL alone cannot establish that condition. Separate failure cache uses name/type/class as a documented model policy, not a universal resolver key. Explicit duration 1–300 seconds, default 5, suppresses the same query until expiry and never produces name-existence evidence. No retry/backoff engine or server-wide failure inference. [RFC 9520 §§2,3.2](https://www.rfc-editor.org/rfc/rfc9520.html).

Before code, freeze insertion/lookup precedence in a short schema specification and table-driven examples: remove conflicting same-owner denials on useful refresh; remove same-type positive data on NODATA; clear owner data/denials on NXDOMAIN; enforce CNAME exclusivity; invalidate matching failure entries on a useful result. Reject a failure insertion while reusable useful data already answers that query. Expired data cannot participate in conflicts. These transitions are conservative teaching-model policy and must be labeled as such.

Architecture: bounded JSON loader and schema validator → pure replay/cache engine → deterministic renderer. No wall-clock calls or sleeps in the replay engine. Records include cache key, insertion/expiry time, remaining lifetime, decision and explanation. Keep input-derived text safe for terminal output through restricted names/data and reject control characters.

## Alternatives and recommendation

Build this small offline model. dnspython is a useful real DNS toolkit with cache tests, but adapting its networking-oriented answer objects and wall-clock expiry would obscure the learning goal. Unbound is a full C recursive validating resolver with materially broader operational dependencies. Neither will be installed or executed for this lab. See RESEARCH.md for source/license/maintenance limitations.

Alternate: an offline longest-prefix route-selection lab using `ipaddress`, fictional route tables and explicit tie policies. It is simpler, but DNS offers a stronger distinct learning gap after response interpretation. No router/host route edits. Longest-prefix behavior has an official baseline in [RFC 4632 §5.1](https://www.rfc-editor.org/rfc/rfc4632.html#section-5.1). The alternate has not received the same full candidate review and is not approved scope.

## Threat model and verification

Assets: host configuration, local files, accurate learning conclusions. Untrusted boundary: supplied JSON. Risks: excessive memory/CPU, malformed or conflicting semantics, terminal escape injection, misleading certainty, accidental live resolution. Mitigate with strict schema/size limits, bounded traversal and atomic validation, no network imports/calls or subprocesses, restricted fictional data, explicit model limitations and deterministic fixtures. The model does not authenticate source DNS data or defend a real resolver from poisoning.

Tests must exercise actual boundaries and distinctions: zero/before/at/after expiry; refresh replacement; SOA TTL versus MINIMUM in both directions; absent SOA; NXDOMAIN across A/AAAA versus type-specific NODATA; CNAME expiry on each hop, dangling alias, terminal denial and cycle/depth; failure min/max/recovery and type isolation; same-time order; contradictory transitions; names/addresses/control characters; bool/duplicate keys/oversize/decreasing time. Independently calculated expected timelines, not implementation-generated snapshots. Run unittest normally and under `-O`, CLI subprocess checks against temporary fixtures, deterministic repeated replay, compileall, Bandit and ECC self-review. Confirm replay while socket connection APIs are patched to fail. No live resolver comparison is needed or claimed.

## Stages and definitions of done

1. Coordinator reviews this exact scope and resolves any ambiguity. Record approval; no code before it.
2. Freeze schema and transition table, implement pure validator/replay and focused unit tests. Done when semantic examples and adversarial boundaries pass.
3. Add CLI, fictional fixtures and readable demo timeline. Done when CLI errors are bounded, no partial results, normal/optimized checks pass and repeated output matches.
4. Self-review with ECC; fix/retest findings; README/setup/security/learning/state/decisions and source attribution. Done when evidence identifies exact commands/results and limitations. Local repository security baseline if initialization is approved; any hosted publication or checks remain separately authorized and accurately reported.

No new scope after 2026-10-06 08:00 America/New_York. No external publication, messages, scheduler, third-party probes, virtualization changes or work in other projects is included.
