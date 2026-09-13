# Security Policy

## Reporting a Vulnerability

Please do not disclose security vulnerabilities in public issues.

Report vulnerabilities privately through GitHub's repository security reporting
mechanism when available. Include enough information to reproduce the issue,
the affected component, potential impact, and any suggested mitigation.

## Scope

Security-sensitive areas include:

- Tool and permission execution
- MCP protocol and transport boundaries
- Workspace and filesystem access
- Provider integrations
- Runtime policy enforcement
- Secrets and credential handling
- Persistent memory and stored task data
- Multi-agent coordination and governance

Agent OS is a release candidate. Security boundaries should be treated as
defense-in-depth rather than as a guarantee of safety for arbitrary tools or
untrusted environments.
