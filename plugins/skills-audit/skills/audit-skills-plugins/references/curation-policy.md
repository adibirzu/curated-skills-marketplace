# External Project Curation Policy

## Admission gates

A project can move from `review-required` to an approved marketplace plugin only after a reviewer records evidence for every gate:

1. Repository uses public HTTPS and has an identifiable maintainer.
2. Source is pinned to a full 40-character commit SHA.
3. License permits the intended reuse and distribution.
4. Plugin and skill manifests validate with no unresolved placeholders.
5. Source review covers instructions, scripts, hooks, MCP servers, apps, dependencies, and update behavior.
6. No embedded credentials, private topology, personal paths, generated logs, prompts, traces, caches, or local databases exist.
7. Requested filesystem, network, credential, and external-write capabilities are minimal and documented.
8. Tests run in an isolated workspace without production credentials.
9. A human explicitly approves promotion and records the reviewed commit.

## Automatic rejection

Reject projects that use mutable download URLs without a verified digest, obscure source provenance, lack a compatible license, request unnecessary credentials, conceal lifecycle execution, or combine untrusted input, sensitive data access, and unrestricted network egress.

## Promotion model

Keep candidates as metadata only. After approval, vendor the reviewed bytes or add a reviewed plugin directory beneath `plugins/`, preserve license notices, record the source commit and digest, validate locally, and update `.agents/plugins/marketplace.json` in a separate reviewed change.

Never treat `eligible-for-review` as approval. Never auto-install candidates from the generated catalog.
