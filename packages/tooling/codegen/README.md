# `packages/tooling/codegen`

Home for contract-generation and related build helpers.

Phase 2 fixes the workflow direction:

1. export OpenAPI from the FastAPI app
2. generate TypeScript output from that snapshot

The initial implementation is intentionally scaffold-level, but the ownership and invocation pattern should remain stable as concrete generators are added later.
