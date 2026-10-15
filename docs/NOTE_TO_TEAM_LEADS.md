# Briefing Note: In-Assistant AI Usage & Governance for Team Leads

**To**: Meridian Life Sciences Team Leads (`Clinical Operations`, `Regulatory Affairs`, `Finance`, `Human Resources`, `Medical Writing`, `IT Platform`)  
**From**: Enterprise AI Platform Team (`IT Platform`)  
**Subject**: Checking Your Team's AI Usage & Capability Controls Directly in Claude & Gemini  
**Assignment Reference**: `Fullstack-ClaudeGemini-UsageConnector-v1`

---

### Hello Team Leads,

You asked for a friction-free way to understand how your teams are using our enterprise AI assistants—without needing to submit billing tickets or log into cloud consoles.

We have now deployed the **Meridian Usage Connector** directly inside both **Claude Desktop** and **Gemini CLI**. You can now ask natural questions right in your assistant window and get immediate, verified usage and cost analytics.

---

### What You Can Now Ask Directly

Your assistant can now pull authoritative data across both our Claude Enterprise workspace and Google Cloud Vertex AI (Gemini). Simply ask naturally:

1. **Team Usage & Spend**:
   - *"How much AI did my team use last month?"*
   - *"Give me a breakdown of our Claude vs Gemini usage for the last 30 days."*
   - *"What was our total token spend for week 36 (`2026-W36`)?"*
2. **Top Team Contributors**:
   - *"Who were the top 5 users on my team by token volume last week?"*
   - *"Which team members are generating the highest output tokens in Gemini?"*
3. **Current Capability Status**:
   - *"What AI capabilities (web search, code execution, usage connector) are currently enabled for our team?"*

All responses report both **token volumes** (input, output, total) and **reconciled USD cost**.

---

### What You Cannot See (And Why)

To safeguard confidential project data and satisfy GxP/HIPAA compliance standards:

1. **Cross-Team Usage Data**:
   - **What happens**: Asking *"Show me the Finance team's token usage"* will return a structured access denial.
   - **Why**: Usage is strictly scoped to your own group cost centre (`cost_centre`). Teams in Clinical Operations, Medical Writing, and Regulatory Affairs work with sensitive protocol documents and clinical trial submissions. Usage boundaries prevent organizational data leakage.
2. **Changing Production Capability Controls**:
   - **What happens**: You can inspect whether capabilities like `code-execution` or `web-search` are enabled, but attempting to toggle them in production will be declined.
   - **Why**: In our production environment (`prod`), capability provisioning is centrally managed to enforce enterprise security policies, prevent unexpected code runtime execution, and ensure budget guardrails. (In `dev` and `staging` sandbox environments, leads retain toggle privileges for feature testing).

---

### How to Request Changes or Additional Capabilities

- **Need a capability enabled for your team?** (e.g. enabling `code-execution` for Clinical Operations or enabling `usage-connector` for Regulatory Affairs):
  Submit a quick request via the IT Service Portal under **Enterprise AI > Capability Request** or ping the Platform team (`Chloe Dubois` or `Arjun Mehta`). Approvals are processed within 1 business day.
- **Questions or feedback on data reconciliation?**
  Reach out on our internal Slack channel `#enterprise-ai-platform`.

We hope this gives you the visibility you need to budget, plan, and guide your teams effectively!

— **Meridian Enterprise AI Platform Team**
