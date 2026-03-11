# Browser Tool Integration (Phase 7)

## Overview
Integrates dedicated browser automation (Stagehand / PinchTab) as a specialized tool within the native UI Agent framework.

## Delegation Logic
- **Trigger**: The native `AgenticPlanner` triggers `delegate_to_browser_tool` when the task requires deep DOM extraction, headless interaction, or complex web navigation.
- **Background Task**: The browser tool runs as a companion asyncio task, allowing the UI Agent to continue monitoring the system.

## Visual Supervision
- **Supervisor Loop**: The UI Agent performs periodic visual checks (Live API) while the browser tool is active.
- **Safety**: If the supervisor detects that the browser tool is stuck, or if the tool fails internally, the UI Agent automatically aborts the delegation and reverts to native visual-click planning.

## Combined Capabilities
- **Native OS Control**: Typing, window management, and native app switching.
- **Web Specialization**: High-speed, token-efficient DOM scraping and navigation for modern web apps.
