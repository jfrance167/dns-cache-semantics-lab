# DNS Cache Semantics Lab

An offline teaching tool that explains whether a repeated DNS question has reusable cached data, a cached denial, a temporarily cached failure, or needs fresh information. It replays fictional JSON events without making DNS requests or changing the host cache.

## Run

Python 3.11+; no packages required. From this directory:

```powershell
python cache_lab.py examples/cache-timeline.json --format text
python cache_lab.py examples/cache-timeline.json
python -m unittest discover -s tests -v
python -O -m unittest discover -s tests -v
```

The tool reads at most 1 MiB of UTF-8 JSON and writes a complete timeline to stdout after validation/replay/serialization. Exit 0 means successful replay; exit 2 means invalid input or an I/O failure. Errors go to stderr. Output redirection is the caller's responsibility: shell redirection can truncate existing files before the tool runs. The tool has no output-file option.

## Demo

The included scenario stores an alias, an AAAA denial and an A resolution failure. A subsequent A refresh recovers the A query while preserving the unrelated AAAA denial. Its A record is still reusable at 3999ms with 1ms remaining, then expires exactly at 4000ms. The alias remains independently cached.

| Query time | Question | Result |
|---|---|---|
| 1000ms | app.example. A | suppressed_failure; terminal host.example. |
| 3999ms | app.example. A | positive; remaining 1ms |
| 3999ms | app.example. AAAA | NODATA; remaining 6001ms |
| 4000ms | app.example. A | needs_information; alias still live |
| 10000ms | app.example. CNAME | needs_information |

JSON includes independent alias/terminal keys, insertion/expiry times, remaining milliseconds, removal decisions and explanations. See [SCHEMA.md](SCHEMA.md) for the exact version-1 input contract and worked transition examples. The stdout timeline can be saved for demonstrations; no live traffic is included.

## Architecture and security model

`load` bounds bytes/nesting/numbers/strings and rejects duplicate JSON keys; `validate` normalizes the complete schema; `replay` uses a pure in-memory cache with an explicit simulated clock; `render` bounds serialized output before writing. No socket, resolver, subprocess or wall-clock calls occur in the application. Tests use subprocesses only to run this local CLI on fictional temporary files.

Input is untrusted JSON, never executable code. Limits include 256 events, 256 combined retained entries, 32 records per RRset and eight CNAME hops. Expired entries are evicted before transitions/capacity checks. Names are restricted to absolute ASCII `example.` and address data to documentation ranges. See [SECURITY.md](SECURITY.md).

## Learning and limits

A cache miss is not NXDOMAIN. NODATA is type-specific; NXDOMAIN is an exact terminal-name denial in this model. Resolution failure does not establish absence. CNAME and terminal data retain separate lifetimes, and a useful A refresh does not erase an unrelated AAAA denial.

This is an explicitly restricted normalized-event teaching model, not a DNS resolver, packet parser or standards-conformance test. No DNSSEC authentication, ancestor NXDOMAIN inference, referrals, retries/backoff, stale serving, actual cache inspection or resolver comparison. Synthetic input assertions are not authenticated DNS evidence. Cache replacement choices are documented model policies. The [research](RESEARCH.md) explains the sources, alternatives and limitations; [verification](verification/REPORT.md) records actual local checks. Linux execution and hosted CI were not performed.

## License and assistance

Original implementation under [MIT](LICENSE). RFC concepts and candidate architecture research are attributed in RESEARCH.md and SCHEMA/PLAN; no upstream resolver code or RFC code components copied. Codex implemented and reviewed the code. A local Ollama test-idea draft was rejected for incorrect semantics; it was not shipped as an authority. Review was self-review, not an independent audit.

## Publication status

See [publication review](PUBLICATION.md) for the October 5 source snapshot, fresh local checks, evidence boundaries and current hosted-check distinction.
