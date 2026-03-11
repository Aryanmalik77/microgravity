# SYSTEM CATALOG — Registered Tools & Capabilities

*Auto-generated registry of all tools available to the Nanobot Swarm.*
*Last updated: 2026-02-28*

---

## Core Filesystem Tools
| Tool | Status | Description |
|------|--------|-------------|
| 
ead_file | ✅ Healthy | Read file contents from disk |
| write_file | ✅ Healthy | Write/create files on disk |
| edit_file | ✅ Healthy | Edit specific sections of existing files |
| list_dir | ✅ Healthy | List directory contents |

## Shell & Execution
| Tool | Status | Description |
|------|--------|-------------|
| exec | ✅ Healthy | Execute shell commands with timeout control |

## Web & Search
| Tool | Status | Description |
|------|--------|-------------|
| web_fetch | ✅ Healthy | Fetch and parse web page content |
| rowser | ✅ Healthy | Headless browser automation (Selenium/undetected_chromedriver) |

## UI Agent (Desktop Automation)
| Tool | Status | Description |
|------|--------|-------------|
| ui_planner | ✅ Healthy | Multi-modal UI/UX orchestrator. Actions: predict (utility analysis), plan (step-by-step interaction schema), orchestrate (swarm-aware evaluation) |
| ui_executor | ✅ Healthy | Full desktop UI automation engine with CV tracking, hybrid validation, and semantic recovery loops. Use for ALL physical desktop GUI workflows |

> **IMPORTANT**: For ANY task requiring physical desktop interaction (clicking GUI elements, opening apps, navigating desktop software, filling forms in native apps), use ui_planner first to generate a plan, then ui_executor to execute it. These tools are the PRIMARY method for desktop automation.

## Communication
| Tool | Status | Description |
|------|--------|-------------|
| message | ✅ Healthy | Send messages to chat channels (Telegram, Discord, etc.) |
| spawn | ✅ Healthy | Spawn subagent workers for parallel tasks |

## Memory & Context
| Tool | Status | Description |
|------|--------|-------------|
| search_history | ✅ Healthy | Search conversation history |
| update_memory | ✅ Healthy | Write persistent memory entries |
| 
ead_memory | ✅ Healthy | Read persistent memory files |
| semantic_search | ✅ Healthy | Vector-based semantic search across memory |
| ookmark_path | ✅ Healthy | Save frequently used file paths |
| 
ecall_paths | ✅ Healthy | Recall bookmarked paths |

## Code Analysis
| Tool | Status | Description |
|------|--------|-------------|
| outline_code | ✅ Healthy | Generate structural outline of code files |
| nnotate_code | ✅ Healthy | Add contextual annotations to code |

## Swarm Management
| Tool | Status | Description |
|------|--------|-------------|
| swarm_status | ✅ Healthy | View status of all active subagents |
| 	ask_tracker | ✅ Healthy | Manage hierarchical task trees |
| user_profile | ✅ Healthy | Read/update user profile and preferences |

## Credentials & Security
| Tool | Status | Description |
|------|--------|-------------|
| search_credential | ✅ Healthy | Search stored credentials |
| store_credential | ✅ Healthy | Securely store credentials |
| invalidate_credential | ✅ Healthy | Revoke stored credentials |

## Environment
| Tool | Status | Description |
|------|--------|-------------|
| 
ead_env_var | ✅ Healthy | Read environment variables |
| set_env_var | ✅ Healthy | Set environment variables |
| 
ead_logs | ✅ Healthy | Read diagnostic log files |

## Evolution & Self-Improvement
| Tool | Status | Description |
|------|--------|-------------|
| log_issue | ✅ Healthy | Log issues to evolution ledger |
| log_user_feedback | ✅ Healthy | Log user feedback for improvement |
| iew_evolution_report | ✅ Healthy | View evolution/improvement reports |

## Scheduled Tasks
| Tool | Status | Description |
|------|--------|-------------|
| cron | ✅ Healthy | Schedule recurring tasks |
