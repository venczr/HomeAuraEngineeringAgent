# Воспроизведение M1a-v2 / ограниченного M1b

Из корня распакованного пакета R3, PowerShell:

```powershell
python -m venv work/venv
work/venv/Scripts/python -m pip install -r m1a/requirements.txt
work/venv/Scripts/python m1a-v2/test_benchmark.py
work/venv/Scripts/python m1a-v2/test_template.py
Expand-Archive -LiteralPath m1a/ufh-source.zip -DestinationPath work/ufh-source
Push-Location work/ufh-source
npm ci --ignore-scripts --no-audit --no-fund
Pop-Location
node m1a-v2/adapt-ufh.mjs work/ufh-source m1a-v2
work/venv/Scripts/python m1a-v2/check_ufh.py
```

Ожидается: 17/17 checker tests, 5/5 template tests, original UFH и adapted UFH — Fail. Ручной reference и поддержанные параметры шаблона — synthetic Pass, export всегда false. reference.py содержит ручной builder; тесты сохраняют reference.json в envelope с fixture/report. Не запускайте отдельно reference.py поверх опубликованных результатов, если нужен исходный envelope.

Для картинок отдельно установите matplotlib==3.10.8 в среду визуализации и запустите render_comparison.py. Измерения от matplotlib не зависят. Все скрипты работают без CAD и исходников HomeAura. Для npm нужен доступ к registry; source ZIP закреплён на commit и содержит LICENSE/lockfile.

Проверка runtime использует Python3.12.0, Shapely2.1.2/GEOS3.13.1, NumPy2.5.1, Node24.18.0/npm11.16.0. Численные различия последних разрядов допустимы в пределах задокументированных ошибок. SHA256.json относится к опубликованному прогону; повторные тесты могут перезаписать JSON/журналы.

Claude-аудит не воспроизводится автоматически: исходная попытка завершилась expired OAuth, полный ответ сохранён. Скрипты не восстанавливают авторизацию и не объявляют этот gate пройденным.
