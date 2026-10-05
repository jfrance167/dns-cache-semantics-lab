# Research evidence — 2026-10-05

Recommendation: build the original bounded offline teaching model in PLAN.md. Searches were targeted, not exhaustive; no confirmed-security claim for upstream projects.

## Reuse and distinct gap

Read existing `network-forensics-pcap-lab/README.md`, `wireshark-traffic-analysis/README.md`, scanner STATE, and the coordinator successor registry (read only). Existing labs analyze packet evidence; no matching cache-expiry simulator found in the directory/name searches performed. Relevant vault notes reviewed: `DNS Response Evidence and Failure Codes.md` and `CSharp HttpClient Pools DNS and Cookie Boundaries.md`. These establish response/connection context, not this simulator. Do not copy private traffic or actual resolver caches into fixtures.

## Candidates

The connected GitHub integration was unavailable in this chat. Public web access and GitHub's unauthenticated read-only API provided the review; no repository clone, dependency installation or third-party execution.

### dnspython

[Repository](https://github.com/rthalley/dnspython), observed main commit `354a5faf66e2ed21ab2a115b8d4e70643535f3a8`, dated 2026-10-04. [ISC license](https://github.com/rthalley/dnspython/blob/354a5faf66e2ed21ab2a115b8d4e70643535f3a8/LICENSE): retain applicable copyright/permission notices if copying. No copying proposed.

[resolver.py](https://github.com/rthalley/dnspython/blob/354a5faf66e2ed21ab2a115b8d4e70643535f3a8/dns/resolver.py) inspected: answer expiry and Cache/LRU checks use `time.time()`; answer cache keys include query name/type/class, with ANY key for NXDOMAIN. This answer-cache architecture differs from independent RRset/event teaching. Source inspection is not a security audit.

[pyproject](https://github.com/rthalley/dnspython/blob/354a5faf66e2ed21ab2a115b8d4e70643535f3a8/pyproject.toml) has no base runtime dependencies, Python >=3.10, optional crypto/HTTP/QUIC/IDNA extras. Broad protocol support is useful but unnecessary here; dependency count alone says nothing about safety.

[cache tests](https://github.com/rthalley/dnspython/blob/354a5faf66e2ed21ab2a115b8d4e70643535f3a8/tests/test_resolver.py) include fake-clock cache expiry/cleaning. [CI](https://github.com/rthalley/dnspython/blob/354a5faf66e2ed21ab2a115b8d4e70643535f3a8/.github/workflows/ci.yml) includes Linux/Windows Python matrices. Tests and hosted results were not run or independently validated. Workflow excerpt uses release tags; do not inherit that practice in Jake's CI.

[Issue 1309](https://github.com/rthalley/dnspython/issues/1309) reports WKS bounds/canonicalization; public API reports closed, while cached web listing showed open. This is outside proposed A/AAAA/CNAME scope and illustrates why active issue listings are not proof of defect absence. No Scorecard obtained. Actual main commit activity and tests are maintenance evidence, not guarantees.

### Unbound

[Repository](https://github.com/NLnetLabs/unbound), observed master `eafb02716650266f886def92dd7487b2831a96f3`, dated 2026-10-02. [License](https://github.com/NLnetLabs/unbound/blob/eafb02716650266f886def92dd7487b2831a96f3/LICENSE) has BSD-style notice, redistribution and non-endorsement conditions. [Official description](https://nlnetlabs.nl/projects/unbound/about/) describes a recursive validating resolver.

[msgreply.c](https://github.com/NLnetLabs/unbound/blob/eafb02716650266f886def92dd7487b2831a96f3/util/data/msgreply.c) inspected: SOA minimum TTL extraction, negative TTL handling, configuration caps and serve-expired handling. This demonstrates operational policy beyond the proposed model. [testcode](https://github.com/NLnetLabs/unbound/tree/master/testcode) exists; no build or test results verified. C runtime/library/daemon surface is disproportionate here. Prefer as future isolated resolver-comparison research, not this lab's dependency.

## Standards and limits

PLAN.md links the official RFC sections that ground its selected semantics. Review also included [RFC 8020](https://www.rfc-editor.org/rfc/rfc8020.html): descendant denial inference is excluded explicitly, so exact-name behavior must not be described as a complete modern resolver.

Errata checked through current RFC info links. [RFC 2308 errata](https://errata.rfc-editor.org/search/?rfc_number=2308) displayed three verified editorial corrections and four held-for-update entries; [RFC 9520 errata](https://errata.rfc-editor.org/search/?rfc_number=9520) displayed verified editorial reference correction 7838. Original `/errata/rfc...` reads failed; the linked replacement worked. No blanket standards-compliance conclusion follows.

Some raw GitHub fetches failed; content API supplied cache tests/CI and current commit/issue metadata. Upstream branches can move. No frozen upstream snapshot or executed upstream verification is claimed.

## Worker review

Local Ollama qwen3.5:2b bounded test-idea task: first invocation blocked by sandbox loopback EACCES before inference; permitted invocation completed in 2668 ms, 313 reported output tokens, stop reason. Raw draft preserved in research/. Rejected: repeatedly treats cache miss/expiry as NXDOMAIN, lacks CNAME TTL inputs, confuses SOA-only events and failure timing. No draft adopted as semantic authority.

Previously selected verified-free North draft in this scanner chat returned no usable text. No new remote retry or paid fallback made. The remaining work is standards interpretation/security judgment and correction, retained with Codex. This chat consumes allowance; local drafting does not guarantee savings.
