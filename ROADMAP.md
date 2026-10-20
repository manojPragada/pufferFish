# Roadmap

## Completed

- [x] Runnable standard-library CLI foundation
- [x] Behavioral tests and documented local examples
- [x] Input handling, explicit limitations and setup guide

## Next

- [x] Add configurable sensitive-key patterns and stronger fixture validation
- [x] Add HTTP mock replay with latency/status fault injection
- [ ] Build local fixture browser and response-diff dashboard

## Continuity

2026-10-20: Added recursive positional array diffs, precise nested paths, explicit additions/removals and CLI redaction regression coverage. Five new tests cover nested values, null, type changes and insertion semantics. Next: the local read-only fixture/diff dashboard; no dashboard is claimed by this change.

Initial foundation implemented and checked on 2026-10-17. Inspect current code and commits before continuing. Prioritize the first unchecked item and keep improvements small enough to verify. No visual dashboard has been implemented.


2026-10-18: Added additive case-insensitive key globs to record/replay/diff, plus replay fixture validation and redaction. Nine behavioral tests pass. Next: local HTTP mock replay and fault injection.


2026-10-19: Added loopback-only GET/HEAD fixture server with fixed latency/status injection and redacted bodies. Recorded headers are omitted. Next: local fixture browser and response-diff dashboard.

