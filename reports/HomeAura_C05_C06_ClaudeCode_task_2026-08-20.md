# HomeAura C05/C06 — независимый инженерный аудит и исправление

Работай в режиме максимального рассуждения. Сначала полностью прочитай обязательный регламент:

`reports/HomeAura_owner_floor_heating_routing_rules_for_all_helpers_2026-08-20.md`

Обязательно изучи оба проекта владельца целиком. Считай их эталоном формы улиток и пучков, но не копируй кухонные пустоты: в текущем проекте необъяснимых незакатанных белых зон быть не должно.

Затем прочитай/осмотри:

- официальный источник: `homeaura-native-editor/examples/proposals/HA_TWO_FLOOR_C12_BOUNDED_TERMINAL_185/HomeAura_TwoFloor_C12BoundedTerminal_D185.homeaura.json`;
- чистый план: `homeaura-native-editor/examples/proposals/HA_TWO_FLOOR_C12_BOUNDED_TERMINAL_185/HomeAura_Floor1_D185_Clean_View.png`;
- ответ ChatGPT: `reports/HomeAura_C05_C06_ChatGPT56Sol_response_2026-08-20.md`;
- evaluator: `homeaura-native-editor-generate/evaluate_chatgpt_c05_c06_candidate_20260820.py`;
- все summary/diagnostics/PNG в `tmp/chatgpt_c05c06_solver_20260820/`;
- все стены, окна, соседние контуры и S_BEND из официального JSON, особенно C07 рядом с C05/C06.

Цель: найти owner-style решение C05/C06 как две настоящие встречные улитки с короткими ортогональными TRANSIT, без диагоналей, без скрытой длины, без пересечений с C07 и другими трубами. Нельзя менять официальный D185 и production-код.

Обязательные гейты: полный регламент; BODY внутри домена; стены/повороты 0; R80; self/inter 0 с учётом всех соседних Point3 и S_BEND; покрытие >=96%, max gap <=200, over200=0; 3x100/окна; длина 40–80 м; парный spread <=2 м; одна непрерывная труба; морфология как в эталонах, не доминирующая змейка.

Сделай независимый разбор причин провала текущих вариантов. Затем предложи точные Point3-массивы C05/C06, BODY ranges, vertical transitions и краткий способ проверки. Если all-gate решение не найдено, не выдумывай PASS: дай минимальный точный blocker и лучший bounded candidate.

Сохрани итог в `reports/HomeAura_C05_C06_ClaudeCode_OpusMax_result_2026-08-20.md`. Разрешены новые scratch-файлы только под `tmp/claude_c05c06_20260820/`. Никаких официальных изменений.
