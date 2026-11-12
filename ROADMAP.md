# Roadmap

## Completed

- [x] Runnable standard-library CLI foundation
- [x] Behavioral tests and documented local examples
- [x] Input handling, explicit limitations and setup guide

## Next

- [x] Add configurable sensitive-key patterns and stronger fixture validation
- [x] Add HTTP mock replay with latency/status fault injection
- [x] Build local fixture browser and response-diff dashboard
- [x] Add multi-route fixture collections and request matching
- [x] Add bounded allowlisted request-header matching
- [x] Add opt-in request-body digest matching without retaining body content
- [x] Add bounded local helper for safe body-digest fixture authoring

## Continuity

2026-11-12: Split the dashboard's content-free changed count into same-type value changes and JSON type changes while preserving the existing total. The API and UI expose counts only, never paths or values. Next: keep dashboard authoring read-only and any future fixture authoring narrower than raw editing.

2026-11-11: Added a content-free diff summary to the dashboard API and UI, separating added, removed and changed counts without including paths or values in the summary. Detailed redacted local paths remain available in the existing comparison list. Next: keep dashboard authoring read-only and any future fixture authoring narrower than raw editing.

2026-11-10: Added content-free fixture capability inspection to the local dashboard. The API and UI expose only validated fixture kind, route count and supported methods—never paths, matcher values, digests or response content. Next: keep dashboard authoring read-only and any future fixture authoring narrower than raw editing.

2026-11-09: Added a read-only `fixture-check` command that runs the complete replay validator and reports only fixture kind, route count and methods, never paths, matcher values, digests or response content. Next: keep fixture authoring deliberately narrower than raw editing.

2026-11-08: Rejected unsupported or malformed route request fields instead of silently ignoring them, preventing hand-edited fixtures from appearing to match on credentials or other unimplemented inputs. Next: keep fixture authoring deliberately narrower than raw editing.

2026-11-07: Closed the route-path validation gap for ASCII DEL in both authored and hand-edited collections, matching the documented control-free contract. Next: keep fixture authoring deliberately narrower than raw editing.

2026-11-06: Rejected every ASCII control character, including tabs and DEL, from exact header matcher values in both authored and hand-edited route collections. Next: keep fixture authoring deliberately narrower than raw editing.

2026-11-05: Tightened custom matcher names to reject repeated hyphens anywhere in the `X-Puffer-*` suffix, keeping authored and hand-edited collections under the same conservative grammar. Next: keep authoring deliberately narrower than raw fixture editing.

2026-11-04: Tightened custom matcher names to bounded, well-formed `X-Puffer-*` fields, rejecting empty suffixes, repeated separators and oversized names before replay. Next: keep authoring deliberately narrower than raw fixture editing.

2026-11-03: Extended equal-specificity ambiguity rejection across header and body-digest matchers, closing an order-dependent tie when one route matched a header and another matched the same request body. Next: keep authoring deliberately narrower than raw fixture editing.

2026-11-02: Rejected overlapping equal-specificity replay routes, preventing route order from silently deciding which fixture wins when header matchers are simultaneously satisfiable. Next: keep authoring deliberately narrower than raw fixture editing.

2026-11-01: Bounded authored and loaded route paths to 2,048 characters and rejected control characters before matching. This keeps route collections safe for the local HTTP server without changing exact-match semantics. Next: keep authoring deliberately narrower than raw fixture editing.

2026-10-31: Added repeatable `--match-header NAME=VALUE` authoring to both route commands, delegated to the replay server's existing allowlist and bounds so credentials and arbitrary headers remain rejected. Next: keep authoring deliberately narrower than raw fixture editing.

2026-10-30: Added bounded, copy-on-write `fixture-append` authoring with source validation, duplicate rejection, the existing 100-route cap and exclusive output creation. Next: consider allowlisted match-header authoring without accepting sensitive headers.

2026-10-29: Corrected `fixture-route` output to use the replay server's validated request envelope, with an interoperability regression test for paths and POST digests. Next: bounded append support with duplicate-route rejection.

2026-10-28: Added exclusive-output `fixture-route` authoring for one safe GET/HEAD/POST route, including optional validated POST digest matching without copying body content. Next: bounded append support with duplicate-route rejection.

2026-10-27: Added a bounded `body-digest` command that hashes at most 1 MiB from a local file without storing or echoing its content. Next: consider a fixture-authoring command that preserves exclusive creation and redaction guarantees.

2026-10-26: Added bounded POST replay selected by an optional lowercase SHA-256 body digest. The server hashes at most 1 MiB in memory and neither stores nor echoes request content. Next: add fixture-authoring guidance or helper tooling for safe digest generation.

2026-10-25: Added bounded exact matching for Accept, Content-Type and X-Puffer-* request headers. Sensitive/arbitrary headers and request bodies remain unsupported; the most-specific match wins. Next: evaluate opt-in JSON body matching with redaction-first storage semantics.

2026-10-24: Added bounded multi-route fixture collections with exact GET/HEAD path matching, duplicate rejection and safe JSON 404 responses. Legacy fixtures remain wildcard-compatible. Next: explicitly allowlisted request header/body matching without storing secrets.

2026-10-21: Added a loopback-only, read-only fixture dashboard with responsive UI, fixture previews, structural comparisons, pre-delivery redaction, traversal protection and API tests. Next: multi-route fixture collections and request matching.

2026-10-20: Added recursive positional array diffs, precise nested paths, explicit additions/removals and CLI redaction regression coverage. Five new tests cover nested values, null, type changes and insertion semantics. Next: the local read-only fixture/diff dashboard; no dashboard is claimed by this change.

Initial foundation implemented and checked on 2026-10-17. Inspect current code and commits before continuing. Prioritize the first unchecked item and keep improvements small enough to verify. No visual dashboard has been implemented.


2026-10-18: Added additive case-insensitive key globs to record/replay/diff, plus replay fixture validation and redaction. Nine behavioral tests pass. Next: local HTTP mock replay and fault injection.


2026-10-19: Added loopback-only GET/HEAD fixture server with fixed latency/status injection and redacted bodies. Recorded headers are omitted. Next: local fixture browser and response-diff dashboard.

