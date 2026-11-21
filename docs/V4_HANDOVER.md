> **Historical reference — not the Final specification.** This file documents an earlier release. For the confirmed six-task Final flow, data and deployment procedures, see [README_FINAL.md](../README_FINAL.md) and the `FINAL_*` documents.

# Handover

This is a standalone, synthetic-only source packaging candidate, not a deployment approval. Review V4_RELEASE_AUDIT.md, V4_TEST_RESULTS.md, V4_POSTGRESQL_CHECK.md, V4_HEROKU_READINESS.md, V4_GITHUB_MANIFEST.md and V4_DEPLOYMENT_RUNBOOK.md in that order. The Live Guard and synthetic-only restrictions are intact.

To achieve deployment readiness, add and test a compatible PostgreSQL driver on Linux, prove transactions/replay/timing on isolated PostgreSQL, confirm Heroku app resources and production settings, and obtain any necessary branding, privacy and researcher approvals. The original project remains separate; never use its database as a release-test database. The package is located in an operating-system temporary directory in this audit and should be copied to a durable approved location after review. No code was pushed, deployed, opened to participants, or used to create paid resources.
