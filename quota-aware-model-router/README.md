# HomeAura quota-aware model router

Этот пакет выбирает агента, модель и глубину рассуждения на границе атомарной задачи. Он не меняет модель внутри длинной сессии: у Kimi Code и Claude Code смена модели или effort инвалидирует prompt cache и заставляет заново загружать историю.

## Что автоматизировано

- локальные детерминированные операции сначала выполняются без LLM;
- маршрутизация учитывает тип задачи, риск, остаток квоты, активного писателя, размер контекста и ожидаемый размер входа;
- Codex и Kimi никогда не пишут одновременно;
- Claude используется только как независимый read-only reviewer;
- новая модель запускается только в новой сессии после checkpoint;
- rate limit, max tokens, неоднозначное завершение и неизвестная квота закрываются fail-closed без автоматического retry или платного fallback.

## Базовая таблица

| Работа | Агент | Модель | Effort |
|---|---|---|---|
| Hash, inventory, schema check, build/test с известной командой | локально | нет LLM | нет |
| Механическая работа Codex | Codex | `gpt-5.6-luna` | `low` |
| Обычная разработка Codex | Codex | `gpt-5.6-terra` | `medium` |
| Сложная разработка Codex | Codex | `gpt-5.6-terra` | `high` |
| Security/claim/credential logic Codex | Codex | `gpt-5.6-sol` | `high` |
| Механическая и обычная работа Kimi | Kimi | `k3-256k` | `low` |
| Сложная/security работа Kimi | Kimi | `k3-256k` | `high` |
| Простая независимая сверка | Claude | `haiku` | не применяется |
| Обычное независимое ревью | Claude | `sonnet` | `high` |
| Security/governance/stage-gate ревью | Claude | `opus` | `high` |

`k3` с 1M контекста допускается только после удаления дублей, при измеренном входе свыше 200 000 токенов, наличии минимум 40 000 токенов резерва, отсутствии видео и подтверждённом entitlement. `kimi-for-coding-highspeed`, Codex Ultra, Claude Fable/Max/Ultracode по умолчанию запрещены.

## Быстрый запуск

Сначала обновите `06_QUOTA_STATE_CURRENT.json` по фактическим `/usage` или owner-reported данным. Неизвестная или просроченная квота считается RED.

Проверить решение без запуска модели:

```powershell
$router = 'C:\AI\HomeAuraEngineeringAgent\quota-aware-model-router'
$powershell = "$env:SystemRoot\System32\WindowsPowerShell\v1.0\powershell.exe"
& $powershell -NoProfile -ExecutionPolicy Bypass -File "$router\Resolve-HomeAuraModelRoute.ps1" `
  -TaskClass routine_code `
  -PreferredAgent auto `
  -QuotaStatePath "$router\06_QUOTA_STATE_CURRENT.json" `
  -ContextPercent 0 `
  -EstimatedInputTokens 40000 `
  -ExpectedOutputTokens 12000 `
  -ActiveWriter none `
  -NoVideo `
  -ContextPruned
```

Подготовить план запуска:

```powershell
& $powershell -NoProfile -ExecutionPolicy Bypass -File "$router\Start-HomeAuraRoutedSession.ps1" `
  -TaskClass routine_code `
  -PreferredAgent auto `
  -QuotaStatePath "$router\06_QUOTA_STATE_CURRENT.json" `
  -TaskPromptFile 'C:\AI\HomeAuraEngineeringAgent\KIMI_REV009_RESUME_20260730T2311.txt' `
  -NoVideo `
  -ContextPruned
```

Чтобы действительно открыть выбранную новую сессию, добавьте `-Launch`. Все окна открываются видимо. Для Kimi краткий bootstrap копируется в буфер обмена: после открытия Kimi вставьте его один раз. Это единственный ручной шаг, потому что Kimi Code 0.31.0 не допускает `--prompt` вместе с `--auto`.

Для текущего rev-009 после фактического reset Kimi сначала обновите Kimi-поля в `06_QUOTA_STATE_CURRENT.json`, затем используйте сложный/security маршрут:

```powershell
& $powershell -NoProfile -ExecutionPolicy Bypass -File "$router\Start-HomeAuraRoutedSession.ps1" `
  -TaskClass security_critical `
  -PreferredAgent kimi `
  -QuotaStatePath "$router\06_QUOTA_STATE_CURRENT.json" `
  -TaskPromptFile 'C:\AI\HomeAuraEngineeringAgent\KIMI_REV009_RESUME_20260730T2311.txt' `
  -ContextPercent 0 `
  -EstimatedInputTokens 120000 `
  -ExpectedOutputTokens 24000 `
  -EstimatedAtomicCostPercent 15 `
  -ActiveWriter none `
  -NoVideo `
  -ContextPruned `
  -Launch
```

## Как агент запрашивает смену

Каждый агент обязан закончить атомарный шаг, записать checkpoint, освободить writer lease и вернуть один объект:

```json
{"schema":"homeaura.model-route-request.v1","task_class":"routine_code","current_agent":"kimi","requested_agent":"codex","reason":"KIMI_QUOTA_RED","checkpoint_path":"C:\\absolute\\path\\checkpoint.json","checkpoint_sha256":"64 lowercase hex","writer_lease_released":true,"no_provider_retry":true}
```

Внешний маршрутизатор проверяет состояние и открывает новую сессию. Сам агент не должен использовать `/model` посреди длинной сессии и не должен оставлять двух активных писателей.

## Текущая HomeAura граница

Этот пакет не изменяет candidate-rev-009, rev-008/rev-004 claims, attempt-010, attempt-011, репозиторий или governance evidence. Он не запускает provider request и не читает Credential Manager. Текущее состояние квот в `06_QUOTA_STATE_CURRENT.json` является owner-reported снимком и после reset должно быть обновлено.

## Почему это не было внедрено раньше

Оркестрация сначала оптимизировалась под exact-byte governance, claims и независимое ревью. Квоты считались внешним ресурсом каждой отдельной сессии, а не общей планируемой ёмкостью проекта. После передачи Codex → Kimi и роста Kimi-контекста до 164k/256k стало видно, что это архитектурный пробел. Простое переключение моделей раньше было бы вредным: оно сбрасывает кэш и увеличивает повторный input. Этот пакет исправляет именно пробел управления ёмкостью — маршрутизацией между короткими сессиями.
