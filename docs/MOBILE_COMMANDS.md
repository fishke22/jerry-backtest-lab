# Mobile Command Model

The user does not need to remember file paths or JSON schemas. The installed Skill should translate natural-language intent into the registered workflow request.

Examples of intended commands:

- "跑 JNU V2.2 日線代理候選，資料到昨天，照正式驗證門檻。"
- "把第一引擎通過的 JNU 候選送 Nautilus 第二引擎。"
- "讀最新 JNU 研究，只告訴我通過、失敗與失敗原因。"
- "用既有快取重跑，不要下載新資料。"
- "強制刷新資料後重跑。"
- "建立一個新聞情緒研究工作流，先提出資料來源、時間戳規則、去重與驗證設計，不要直接施工。"

The Skill resolves these commands against `config/workflow_registry.json`, writes the appropriate versioned request, lets the cloud workflow execute, and reads the committed result back.

New domains should be added as new workflow families. Do not grow one universal script that mixes unrelated research logic.
