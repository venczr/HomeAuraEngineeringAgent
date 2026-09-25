# ChatGPT 5.6 Sol response — C05/C06

Source conversation: `https://chatgpt.com/c/6a875110-759c-83eb-9bcd-27e45cebad2e`

Model/UI context supplied by owner: ChatGPT 5.6 Sol, «Очень высокий».

Extracted from the completed Edge conversation on 2026-08-20. This is external design input, not accepted project geometry.

```text
C05_BODY=[(16400,9200),(18200,9200),(18200,11600),(16400,11600),(16400,9600),(17800,9600),(17800,11200),(16800,11200),(16800,10000),(17400,10000),(17400,10800),(17200,10800),(17200,10200),(17000,10200),(17000,11000),(17600,11000),(17600,9800),(16600,9800),(16600,11400),(18000,11400),(18000,9400),(16400,9400)]
C05_POST_TRANSIT=[(16400,9400,108),(16400,9200,135),(17000,9100,135)]
C06_BODY=[(20600,11600),(18400,11600),(18400,9200),(20600,9200),(20600,11200),(18800,11200),(18800,9600),(20200,9600),(20200,10800),(19200,10800),(19200,10000),(19800,10000),(19800,10400),(19600,10400),(19600,10200),(19400,10200),(19400,10600),(20000,10600),(20000,9800),(19000,9800),(19000,11000),(20400,11000),(20400,9400),(18600,9400),(18600,11400),(20600,11400)]
C06_POST_TRANSIT=[(20600,11400,108),(20600,11200,70),(17000,9400,70)]
```

## External model's morphology claim

- C05: inward branch indices 0–11, centre turn 11→12→13, outward branch 13–21; adjacent supply/return terminals on the west side.
- C06: inward branch indices 0–13, centre turn 13→14→15, outward branch 15–25; adjacent supply/return terminals on the east side.
- Both bodies are claimed as 200 mm interleaved counterflow spirals, not room-scale serpentines.

## External model's numerical claim

- Raw full lengths: C05 41.010 m, C06 42.429 m; spread 1.418 m.
- Estimated R80 lengths: C05 about 40.197 m, C06 about 41.525 m; spread about 1.328 m.
- Estimated per-territory coverage: C05 about 97.98%, C06 about 97.93%.
- Claimed minimum same-level pitch 200 mm and minimum surface clearance 11 mm.

## Local review boundary

The response's two final POST_TRANSIT legs are diagonal in plan:

- C05 `(16400,9200,135) → (17000,9100,135)`;
- C06 `(20600,11200,70) → (17000,9400,70)`.

Those legs violate HomeAura's orthogonal Point3 route contract. Therefore all external numerical claims remain unaccepted until the exact candidate and a minimally orthogonalized variant pass the native analyzer, physical R80 coverage, wall, global-contact, and visual morphology checks.
