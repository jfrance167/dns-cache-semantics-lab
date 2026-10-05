# Frozen version 1 contract

Approved addendum reviewed before implementation. Policy choices below are the simulator's normalized-event model, not a complete resolver implementation.

Envelope: exactly `version` (integer 1) and `events` (array). Each event has integer `at_ms`, `op`, `name`, `type`. IN class is implicit. Event time is 0..86400000, nondecreasing; equal-time events execute in input order. Every name is absolute under `example.`, ASCII LDH labels (1..63, no leading/trailing hyphen), total presentation length <=254 including final dot. Canonicalization lowercases names. Types A, AAAA, CNAME; negative/failure only A or AAAA.

Operations and additional fields:

| op | Additional fields |
|---|---|
| query | none |
| store_rrset | ttl_s (0..86400), records (1..32 strings); CNAME exactly one target |
| store_negative | kind NXDOMAIN/NODATA, soa optionally {owner,ttl_s,minimum_s}; missing soa means uncached |
| store_failure | duration_s (1..300, optional default 5); this is a completed resolution failure, not a single SERVFAIL packet |

A records use 192.0.2.0/24, 198.51.100.0/24 or 203.0.113.0/24; AAAA uses 2001:db8::/32. Duplicate canonical records rejected; record ordering retained. SOA owner is a label-boundary ancestor including equal name. TTL is uniform per RRset. All unknown keys and types rejected. No escaped/binary labels, IDNA or raw message inference.

Input: UTF-8, <=1MiB; lexical JSON nesting <=8, numeric token <=12 characters, decoded string <=254 characters. No floats/constants, duplicate keys, bool-as-integer, controls, lone surrogates or BOM. At most 256 events, total combined retained cache <=256 entries. Evict expired entries before every event and before conflict/capacity checks. Output <=1MiB; whole replay/serialization completes before stdout write. Loader failures and semantic errors produce no partial timeline. CLI writes stdout only; input read is bounded and has no output-file alias hazards.

## Transition table (expired entries removed first)

| Insertion | Removal/recovery policy |
|---|---|
| A/AAAA RRset | same-owner NXDOMAIN and matching-type NODATA; owner CNAME; replace matching RRset; clear matching terminal failure |
| CNAME RRset | owner A/AAAA RRsets and all owner denials/failures; replace owner CNAME; singular target |
| NXDOMAIN | reject if owner currently CNAME; clear owner RRsets/denials/failures; insert name-wide negative |
| NODATA(A/AAAA) | reject if owner currently CNAME; remove matching-type positive/NODATA/failure and name-wide NXDOMAIN; preserve unrelated type |
| missing-SOA negative / TTL-zero insertion | report uncached; do not alter reusable state |
| completed failure | reject if cached positive/negative data can answer the query (including through CNAME); replace same terminal tuple's failure only; must target terminal, never a currently cached alias |

Useful terminal refresh clears that terminal's matching failure; refreshing an alias does not erase unrelated terminal failure. Contradictory alias denial/failure input rejected because negative events must name the terminal. An address RRset replaces a cached CNAME under this explicit model policy; CNAME insertion replaces owner address data, never terminal target data.

Lookup: direct CNAME query returns only CNAME or miss. A/AAAA query traverses live aliases (maximum 8 hops), then checks terminal positive, NXDOMAIN, NODATA, failure, miss. Report hop keys and lifetimes separately. Cycle/depth results are model errors, not cached denials. A miss or expiry never means absent. NXDOMAIN matches both A and AAAA at that exact terminal name, not descendant names. Failure suppresses only the documented terminal query tuple and never asserts absence. Remaining lifetime is exact ms; no rounded TTL extends expiry.

## Independently worked examples

- At 0 store A for host.example. TTL 2. Query at 1999 → positive, remaining 1ms; at 2000 → needs_information.
- Store NODATA(A), then NODATA(AAAA), both TTL min(30,10)=10. Refresh A at 1000 with TTL 20: A positive; AAAA still NODATA with 9000ms remaining.
- Store NXDOMAIN missing.example. TTL min(10,30)=10: A and AAAA negative before 10000; child.missing.example. miss. Refresh A at 1000: NXDOMAIN cleared, AAAA miss.
- Alias at 0 TTL 2 to target.example.; terminal A TTL 10. At 1999 alias query positive with hop remaining 1ms and terminal remaining 8001ms; at 2000 alias miss while direct target remains positive.
- Alias TTL 10; terminal A TTL 2. At 2000 alias query needs_information for terminal with live alias; it does not extend terminal lifetime.
- Alias TTL 10; terminal NXDOMAIN TTL 5: result denies target, preserves alias. Direct CNAME query still positive.
- Terminal completed failure at 0 duration 5: query at 4999 suppressed; at 5000 miss. A refresh at 1000 clears only matching failure; unrelated AAAA failure preserved.
- A→B→A live CNAME cycle returns alias_cycle, no denial. Ninth hop returns alias_depth; eight hops plus a terminal answer is allowed.

Version 1 does not promise RFC compliance outside this subset. Further schema/semantic expansion needs a new reviewed plan.
