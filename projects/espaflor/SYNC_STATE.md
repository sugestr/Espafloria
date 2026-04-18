<!-- v: 2 | updated: 2026-04-18T19:10Z -->
# SYNC_STATE

**Это координационный файл для multi-chat архитектуры.**
Он отвечает на вопрос: **«синхронизирована ли база в Project knowledge с GitHub?»**

---

## Текущее состояние

```yaml
# Что загружено в Claude Project knowledge
project_knowledge_version:
  last_updated: 2026-04-18T19:10:00Z
  uploaded_by: Andriy
  base_commit: 9cd7d5675147b6362caa17dfe8bce5ab8898d59f

# GitHub repo (source of truth)
github_repo:
  url: https://github.com/sugestr/espafloria
  branch: main
  latest_commit: 9cd7d5675147b6362caa17dfe8bce5ab8898d59f
  last_commit_date: 2026-04-18

# Cinema check
sync_status: synced
```

---

## 📋 Протокол для каждого чата

### При старте новой сессии (обязательно)

1. **Прочитай этот файл** из Project knowledge
2. **Через `github:get_file_contents`** прочитай `SYNC_STATE.md` в main branch
3. **Сравни:**
   - `project_knowledge_version.base_commit` (из Project)
   - `github_repo.latest_commit` (из GitHub API)
4. **Если совпадают** → `sync_status: synced` → работай нормально
5. **Если НЕ совпадают** → `sync_status: outdated` → **alert Owner'у:**

   > ⚠️ **База знаний в Project knowledge устарела.**
   >
   > В GitHub есть новее commit `abc1234` от YYYY-MM-DD, а в Project загружен `def5678` от YYYY-MM-DD.
   >
   > Варианты:
   > - **Обновить Project knowledge** (рекомендую, 30 секунд): скачать ZIP с GitHub → upload в Project
   > - **Работать со старой версией** (рискуем пропустить свежие решения)
   > - **Пропустить sync** (если задача не касается обновлённых файлов)
   >
   > Что выбираете?

### После коммита в GitHub

1. **Обнови** поле `github_repo.latest_commit` + `last_commit_date` в этом файле
2. **Закоммить** обновлённый `SYNC_STATE.md` вместе с другими изменениями
3. **В последнем сообщении Owner'у** обязательно:

   ```markdown
   📌 **Обновление**
   - Commit: `<sha>` "краткое описание"
   - Изменённые файлы: [...]
   - **Перезалейте в Project knowledge:** скачайте с GitHub и upload в UI
   - После upload — обновите `project_knowledge_version.base_commit` в SYNC_STATE.md
   ```

### После upload в Project knowledge (делает Owner)

Owner может:
- **Сам** обновить SYNC_STATE.md (в следующем чате, с объяснением — «я залил, обнови sync state на коммит X»)
- **Или** попросить любого worker-чата это сделать как первое действие

---

## ❓ FAQ

**Q: Зачем этот файл, если есть VERSIONS.md?**
A: VERSIONS.md отвечает «какие версии файлов в моей базе?». SYNC_STATE.md отвечает «моя база вообще актуальна?». Это разные уровни.

**Q: Что если несколько workers работают параллельно?**
A: Плохой паттерн. Один worker = одна задача = один поток коммитов. Параллельность — через orchestrator, который сериализует.

**Q: А если Owner забыл обновить после коммита?**
A: Следующий чат увидит `outdated` и напомнит. Owner обновит — цикл замкнётся.

**Q: Можно автоматически?**
A: Пока нет MCP-интеграции GitHub ↔ Project knowledge. Это open work.

---

См. [12_ai_workflow.md](12_ai_workflow.md) для полной архитектуры.
