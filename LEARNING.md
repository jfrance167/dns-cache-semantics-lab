# Learning

Cached absence, absence of a cached answer and failure to resolve are three distinct outcomes. A simulator that maps expiry to NXDOMAIN teaches a dangerous false inference; the local draft made this mistake and was rejected.

Cache keys encode scope: NXDOMAIN covers an exact terminal name across supported address types; NODATA covers only its type. Refreshing A must not silently erase a still-live AAAA denial. Failure state is separate and expires without becoming evidence of existence or absence.

Following CNAMEs does not merge lifetimes. A target can expire while an alias remains usable, or the alias can expire while a direct target answer remains cached. Exact-boundary tests catch accidental lifetime extension.

Normal tests and `-O` runs use unittest assertions, not application `assert` statements that vanish in optimized Python. Deliberate mutations provide evidence that important tests detect an incorrect implementation.

Optional exercise: change the demo A TTL from 2 to 3 seconds, predict the 4000ms result and remaining lifetime, then replay it. Keep all names/data fictional.
