# Zenith Build Instructions

You (Claude Code, running as Fable 5) are building this project, but you must
never change what model the LIVE APP calls at runtime. The model string in
backend/app/services/claude_service.py must remain a Sonnet-class model
(currently claude-sonnet-5 — updated from claude-sonnet-4-20250514 on
2026-07-16; never change it to a Fable or Mythos-class model). Confirm this
file's model string is unchanged at the end of any session that touches
claude_service.py.
