# Security and authorization

The authorized scope is local offline replay of fictional normalized JSON. No live DNS, network probes, host resolver/cache changes, DNSSEC claims or external publication. The original scanner's pending Linux SYN verification is unrelated and remains pending.

Trust boundary: untrusted input file. The loader caps raw bytes before JSON object decoding; scans nesting before parsing; rejects duplicate keys, non-integer numbers, overlong numeric tokens and unsafe strings. The schema rejects unknown fields, non-fictional names/addresses, oversized record/event collections and ambiguous aliases. Replay has a combined cache limit and bounded alias traversal. It performs no network I/O or external command execution.

Validation and replay errors emit no partial timeline. Serialization completes within the output budget before stdout is written. Physical stdout/I/O failures can still cause partial delivery; there is no transactional guarantee for a pipe, terminal or shell-redirection destination. Input read errors do not echo filenames or raw exception contents.

The simulator trusts the normalized meaning supplied by a fixture; it cannot verify a real server's authority, message integrity, poisoning resistance or name existence. Its failure event means a completed attempt with no useful response from any available server, never a conclusion drawn automatically from one SERVFAIL packet. No source credibility or DNSSEC validation is simulated.

If reporting a bug, supply a minimal fictional JSON reproducer and expected/actual model outcome. Do not include employer/client traffic, credentials, actual resolver cache exports or private network identifiers. No external disclosure channel has been configured or authorized by this project.
