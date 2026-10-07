# Record Diesel, Disposable Energy, and Unemployment — October 2026

*Life requires energy. Less affordable energy, less life.*

**Disposable Energy** is how much energy people can buy with their take-home pay. It measures
the input to the economic flywheel: labor applying affordable energy. Because the flywheel has
momentum, a loss of Disposable Energy shows up in jobs only after a delay.

## Where we are

| | Value | Source |
|---|---|---|
| Diesel, record week (Sep 21, 2026) | **$6.53/gal** — above the June 2022 record of $5.81 | EIA via FRED `GASDESW` |
| Diesel, latest week (Oct 5, 2026) | $6.20/gal | same |
| Diesel, 12-month change (Sep 2026) | **+68%** | same |
| Gasoline, 12-month change (Sep 2026) | +38% | FRED `GASREGW` |
| Disposable Energy per person (1986 = 0) | **+0.66 in Jan 2026 → +0.06 in May → +0.18 in Aug** | FRED `A229RC0`, `GASREGW` |
| Unemployment (Sep 2026) | 4.2% | BLS via FRED `UNRATE` |

The diesel record is in today's dollars. Adjusted for inflation, it roughly matches the June 2022
peak ($6.52 in today's dollars) and is below June 2008 ($7.19). The *speed* of the change is what
matters most for what comes next: Disposable Energy per person lost 0.60 in four months — the
fastest four-month drop since monthly data begin in 1990. The next largest (2020–21) were swings
in stimulus income, not energy.

## What the record says happens next

From 1977 to 2019, a rise in gasoline prices was followed by rising unemployment
**16 to 24 months later**, strongest at 18 months (r = 0.33). Diesel alone shows the same timing,
strongest at 17 months, but weaker (r = 0.29, 1995–2019). See [README.md](README.md) and
`output/results.json`.

Applied to a shock that began in March 2026 and peaked in September 2026:

- **Late 2027 through 2028** is the window when the job effects would be expected to arrive.
- **Before then, prices.** Trucks carry most US freight, and farms, construction, and mining run
  on diesel. Diesel costs pass into the price of food and goods within months, cutting
  Disposable Energy a second time through everything people buy, not just fuel.
- **Momentum hides it.** GDP and unemployment can look healthy through 2027 while the flywheel's
  input has already fallen. That is the pattern of 1998–2008: Disposable Energy peaked in 1998;
  GDP gave no warning before 2008.

The last comparable shock is a guide to the size: gasoline peaked in mid-2022, and unemployment
rose from 3.4% (April 2023) to 4.2% (July 2024). That rise was modest, likely cushioned by
COVID-era money printing still in the economy. Whether money printing cushions this shock, or
adds to the debt drag instead, is the open question.

## Limits

- Correlation around 0.3 means energy prices explain roughly a tenth of the change in
  unemployment. It is a consistent leading signal, not a forecast of a specific number.
- These are national averages. The economy is a confederation of upside-down pyramids: freight-
  and farm-dependent regions feel diesel first and hardest.
- The concept of Disposable Energy is open for review. Academic contributions welcome:
  bill@jpods.com.

## The structural point

Diesel shocks hit hardest where freight moves on roads. Freight railroads move a ton about 470
miles per gallon; trucks are far less efficient per ton-mile. Federal highways shifted freight
from rail to trucks, so every diesel shock now reaches deeper into the cost of living. Energy
self-reliance — solar-powered, grade-separated networks for people and Middle Mile cargo — is
how a city stops importing these shocks.

## Reproduce

```bash
python3 disposable_energy.py   # builds the 1986 base and lag tests
python3 diesel_check.py        # current diesel, Disposable Energy, diesel lag test -> output/diesel_check.json
```
