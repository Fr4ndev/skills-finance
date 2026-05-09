---
name: adk-staff-trading
description: "Advanced Agent Development Kit (ADK) for High-Frequency Trading (HFT) insights, Arkham CEX flows, and security auditing. Use for: market making analysis, CEX flow tracking, AD CS pentesting, and autonomous agent self-improvement."
---

# ADK Staff Trading & Security

This skill implements a high-level autonomous agent infrastructure (Staff AI Engineer level) for trading operations and security auditing. It follows the `.agent/` philosophy for self-cognition and continuous improvement.

## 🧠 Cognitive Loop
1. **Observation**: Deep scan of market data, CEX flows, or AD configurations.
2. **Diagnosis**: Identify imbalances, aggressive flows, or ESC1 vulnerabilities.
3. **Decision**: Formulate bias scores or exploit strategies.
4. **Actuation**: Execute actions via Action Server or CLI tools.
5. **Validation**: Verify impact and accuracy.
6. **Meta-improvement**: Log results and update internal context.

## 🛠 Core Components
- **Market Maker Pro**: Real-time orderbook imbalance and bias scoring.
- **Arkham CEX Tracker**: Smart flow analysis with anti-false-positive walkthrough.
- **Auto ESC1**: Automated AD CS pentesting and impersonation.
- **Self-Cognition**: Scripts for context snapshots, health checks, and self-auditing.

## 📋 Protocols
- **Before Any Action**: Run `scripts/update-context.sh` to ensure reality alignment.
- **Git Hygiene**: All changes must be logged in `changelog-agent.md`.
- **Safety**: Never execute financial orders without manual confirmation (unless specified).

## 📂 Resource Mapping
- **Protocol**: Read `references/CORE-PROTOCOL.md` for operational standards.
- **Trading**: Use `templates/trading/` for MM and Arkham implementations.
- **Security**: Run `scripts/auto_esc1.sh` for AD CS auditing.
- **Maintenance**: Use `scripts/health-check.sh` and `scripts/improve.sh`.

## 🚀 Action Server Integration
This skill is designed to be exposed via Sema4AI Action Server. See `templates/action_server/` for the `@action` decorated entry points.
