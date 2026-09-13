# Contributing

Thanks for contributing to Agent OS.

## Development

Agent OS currently targets Python 3.11+ and uses a standard `src/` package
layout.

Run the test suite with:

    PYTHONPATH=src pytest -q

For stricter resource-lifecycle validation:

    PYTHONPATH=src pytest -q -W error::ResourceWarning

## Pull Requests

Please:

1. Keep changes focused.
2. Add or update tests for behavioral changes.
3. Preserve security and permission boundaries.
4. Run the full test suite before submitting.
5. Run `git diff --check`.
6. Do not commit secrets, credentials, local databases, build artifacts, or
   generated environment files.

## Architecture

The V2 architecture is currently frozen. New changes should normally improve,
harden, test, document, or integrate the existing architecture rather than
introduce another major subsystem.

See `AGENTS.md`, `README.md`, and `V2_ROADMAP.md` for project context.
