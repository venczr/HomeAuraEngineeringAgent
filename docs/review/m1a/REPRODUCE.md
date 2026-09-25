# Воспроизведение M1a

Окружение исходного запуска: Windows, Node 24.18.0, npm 11.16.0, Python 3.12.0. Версии Shapely/GEOS — environment.json. Нужен доступ к registry для установки пакетов. Скрипты не используют HomeAura, CAD, UI или API-ключи.

Из распакованного пакета аудита, PowerShell:

```powershell
Expand-Archive -LiteralPath m1a/ufh-source.zip -DestinationPath work/ufh-source
Push-Location work/ufh-source
npm ci --ignore-scripts --no-audit --no-fund
npm test -- --reporter=verbose
Pop-Location
python -m venv work/venv
work/venv/Scripts/python -m pip install -r m1a/requirements.txt
node m1a/run-candidate.mjs work/ufh-source m1a
work/venv/Scripts/python m1a/check.py
```

Ожидаемые результаты: upstream 76 passed / 5 failed; checker принимает геометрическую змейку и отклоняет 6 мутаций; candidate FAIL, export запрещён. Полного положительного теста бифилярного solver нет. Время вызова меняется между запусками. Runner/checker перезаписывают соответствующие результаты в m1a; исходный ZIP пакета сохраняет опубликованный прогон. SVG — диагностика, не монтажный чертёж.

License/notice: ufh-source.zip содержит оригинальный LICENSE Apache-2.0, package.json и lockfile выбранного commit. Node-зависимости и Python-зависимости имеют собственные лицензии; node_modules не включён в пакет. Исходники HomeAura в этот архив не включены.
