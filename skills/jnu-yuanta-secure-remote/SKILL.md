---
name: jnu-yuanta-secure-remote
description: Govern secure remote Yuanta quote access for JNU Research. Use when designing mobile/cloud access, GitHub deployment, secret storage, or a private read-only JNU MCP endpoint.
version: "1.0.0"
---

# JNU Yuanta Secure Remote

Read `config/jnu_yuanta_remote_access_security_v1.json` before any remote Yuanta design.

Rules:

- GitHub stores code, never broker credentials.
- A password hash cannot authenticate to Yuanta and must never be proposed as a replacement secret.
- Prefer a persistent trusted Windows runtime with Windows Credential Manager or a cloud secret vault.
- GitHub Actions Secrets may support bounded jobs/deployment but do not turn Actions into an always-on realtime quote service.
- A home-PC self-hosted runner still depends on the home PC being online.
- Preferred mobile-independent design is a persistent Windows cloud VM plus a private authenticated quote-only HTTPS/MCP endpoint.
- Do not expose or implement order methods.
- Do not mark remote exact JNU active until a real VM login and exact OSE JNU callback have been observed.
