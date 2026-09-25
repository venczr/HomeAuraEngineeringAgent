# HomeAura C05/C06 — координатный поиск Kimi K3

Используй Kimi K3 и максимально тщательное рассуждение. До расчётов полностью прочитай:

`reports/HomeAura_owner_floor_heating_routing_rules_for_all_helpers_2026-08-20.md`

Обязательно изучи оба проекта владельца целиком. Считай их эталоном формы улиток и пучков, но не копируй кухонные пустоты: в текущем проекте необъяснимых незакатанных белых зон быть не должно.

Входные данные:

- `homeaura-native-editor/examples/proposals/HA_TWO_FLOOR_C12_BOUNDED_TERMINAL_185/HomeAura_TwoFloor_C12BoundedTerminal_D185.homeaura.json`;
- `homeaura-native-editor/examples/proposals/HA_TWO_FLOOR_C12_BOUNDED_TERMINAL_185/HomeAura_Floor1_D185_Clean_View.png`;
- `reports/HomeAura_C05_C06_ChatGPT56Sol_response_2026-08-20.md`;
- `homeaura-native-editor-generate/evaluate_chatgpt_c05_c06_candidate_20260820.py`;
- каталог `tmp/chatgpt_c05c06_solver_20260820/`;
- все соседние трубы/переходы из official D185, не только C05/C06; особо учти C07 S_BEND около x=17400, y=10500..10800.

Цель: независимо выполнить координатный/параметрический поиск C05/C06. Сохрани owner-style bifilar/counterflow morphology. Никаких диагоналей. BODY z=108; service z=70/135; S_BEND_R80 materialized; сетка100; повороты R80; трубы16; минимальная консервативная осевая дистанция25. Все требования и запреты бери из полного регламента.

Нужно перебрать не один рисунок, а варианты ориентации улиток, центральных карманов, терминалов, верхнего/нижнего service split и разнесения по слоям. После каждого варианта используй существующий evaluator/нативные diagnostics. Принимай только: стены/turnwall/R80/self/inter=0; BODY coverage>=96%; max<=200; over=0; 3x100/windows pass; 40–80м; spread<=2м; непрерывность; owner morphology.

Не менять официальный D185 и production-код. Разрешены только `tmp/kimi_c05c06_20260820/` и итоговый отчёт `reports/HomeAura_C05_C06_KimiK3_result_2026-08-20.md`. В отчёте дай точные arrays/ranges/transitions, метрики, SHA файлов и честный PASS/NO-GO.
