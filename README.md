# PufferFish

Record bounded JSON GET responses, redact known credential keys, inspect responses offline, and compare JSON structurally.

**Status:** runnable CLI and local read-only dashboard. No hosted demo is available. Examples use synthetic offline data. Python 3.10+; standard library only. Validated with Python 3.12.

## Quick start

```bash
git clone https://github.com/manojPragada/pufferFish.git
cd pufferFish
python --version
python app.py replay examples/response.json
python app.py diff examples/response.json examples/response.json
```

Use `python3` if your system does not provide `python`. No package installation or API key is needed.

## Usage and behavior

Create a one-route collection from an existing fixture with `python app.py fixture-route fixture.json routes.json --method GET --path /health`. Output uses exclusive creation; POST digests must be lowercase SHA-256 values.

Generate the optional POST body digest without copying request content into a fixture: `python app.py body-digest request.json`. Input is capped at 1 MiB; only the lowercase SHA-256 digest is printed.

Structural diffs now descend into arrays, reporting exact paths such as `$["items"][0]["price"]`, with explicit added/removed entries. Arrays are compared by position, not identity or sequence alignment: inserting an item can report subsequent index changes. Inputs are redacted before comparison; unchanged secrets are not printed. JSON types remain distinct, including `true` versus `1`.

To record an endpoint you control: `python app.py record http://127.0.0.1:8000/data fixture.json`. This sends a GET request, uses a ten-second timeout, refuses automatic redirects and caps the response at 1 MiB. Recording refuses to overwrite an existing file. Replay only prints the saved response; it does not run an HTTP mock server.

Run `python app.py --help` for available options.

## Custom redaction and fixture validation

Use repeatable, case-insensitive key globs on any command; these supplement the built-in sensitive names:

```bash
python app.py replay examples/response.json --redact-key '*_secret' --redact-key 'private-*'
python app.py diff examples/response.json examples/response.json --redact-key '*_secret'
```

Patterns apply recursively to JSON keys and response headers; recording also applies them to URL query keys. Quote globs to prevent shell expansion. Replay now validates fixture version, response status, headers and body presence, then redacts before printing. Validation does not prove that a fixture is free of sensitive data.

## Loopback HTTP mock and fault injection

```bash
python app.py serve examples/response.json --port 8766 --status 503 --delay-ms 250 --redact-key 'private_*'
```

Point a local client at `http://127.0.0.1:8766/any/path`. A legacy fixture replays one redacted JSON body for every GET/HEAD path; no upstream requests are made. Stop with Ctrl+C. Binding is fixed to IPv4 loopback. Port 0 selects an ephemeral port and prints it. Delay is bounded to 0–30000 ms; final status is 200–599. Statuses 204, 205 and 304 omit the body. Recorded headers are not replayed: the server supplies JSON content type, content length and no-store only, apart from standard HTTP server headers. This is a local development server, not an authenticated or production service. It does not simulate random failures.

The serve command also accepts `{"version":1,"routes":[...]}`. Each route is a normal fixture whose `request` contains an exact `method` (`GET`, `HEAD` or `POST`) and absolute `path`; query strings are ignored for matching. A route may add an exact, case-insensitive-name `match_headers` object. To avoid turning fixtures into a credential store, only `Accept`, `Content-Type`, and names beginning `X-Puffer-` are accepted. POST routes may include a lowercase `body_sha256` digest; incoming bodies are capped at 1 MiB, hashed in memory and never stored or echoed. The most-specific matching route wins. Collections are capped at 100 routes, reject identical matchers, and return a safe JSON 404 when unmatched. Digest matching does not prove the original body contained no secrets.

## Local fixture dashboard

```bash
python app.py dashboard examples --port 8765
```

Open http://127.0.0.1:8765, then choose fixtures to preview or compare. The server binds only to IPv4 loopback, reads top-level `.json` files from the chosen directory, validates fixture structure and redacts sensitive keys before sending JSON to the page. The responsive interface makes no external requests. It is read-only: it cannot record, edit, delete or serve fixtures as mocks.

## Development and verification

```bash
python -m unittest discover -s tests -v
python -m compileall -q app.py tests
```

Tests exercise behavior with temporary/local data. PufferFish's recording test uses only a loopback HTTP server. There is no build step or configured linter; compilation is a syntax check, not linting.

## Configuration

Configuration is provided through CLI arguments. No environment variables, `.env` file, credentials or external services are required. `.env.example` documents this intentionally empty configuration contract.

## Structure

```text
app.py          CLI and core domain functions
replay_server.py loopback fixture server
dashboard.py    loopback dashboard server and safe fixture loading
dashboard/      dependency-free responsive browser UI
examples/       synthetic example inputs (queue-lab uses commands above)
tests/          behavioral unit tests
ROADMAP.md      completed work and prioritized next steps
.env.example    configuration notes
```



## Architecture

A single dependency-free module exposes importable core functions and a CLI entry point. Filesystem and network access occur only when the corresponding commands run. This small foundation will be split into a package, integrations and UI as those features arrive; see the roadmap.

## Limitations

Built-in and custom-key redaction is not comprehensive secret detection. Review fixtures before sharing: custom field names, free text, URL paths and non-sensitive query fields can still contain private data. Only JSON responses are supported. No authentication injection or dashboard yet. Mock fault simulation supports fixed latency and status only.

## Running and deployment

Run locally from the repository using the commands above. No hosted deployment has been configured. Do not expose a development process publicly. A web deployment guide will be added when a web application actually exists.

## Troubleshooting

- **Python not found:** install Python 3.10+ or try `python3`.
- **File not found:** run from the repository root or provide an absolute input path.
- **Invalid input:** inspect the error printed to standard error and compare with the examples.
- **Permission denied:** choose a folder you own; avoid running as administrator.

## Contributing and credits

Open an issue describing the observed behavior, expected result and a minimal synthetic example. Keep changes focused, include behavioral tests, run the checks above, and update this README when commands or capabilities change. Do not submit credentials or private input files.

Implementation and synthetic examples are original to this repository. There are no third-party runtime dependencies or media assets. A redistribution license has not yet been selected; public visibility alone does not grant an open-source license.



