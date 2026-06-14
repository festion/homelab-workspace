# MCP Servers Learnings

> Project-specific learnings for the mcp-servers repository.

---

### Legacy committed node_modules
- This repo has node_modules tracked in git (legacy pattern, .gitignore was added later). When working with tracked node_modules, use `git add -u` (modified/deleted only), never `git add -f`.
