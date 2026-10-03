# Better tides on your Casio G-Shock GBX-100

*Accurate, offline tide predictions on the GBX-100 (module 3482) from official tide-gauge data, uploaded over Bluetooth LE. — [Version française](README.fr.md)*

The GBX-100 has a nice tide graph, but for many ports the data that the **CASIO WATCHES** app sends is crude, and high/low water times can be off by more than an hour. This project computes **proper harmonic tide constants** from official measurements and uploads them to the watch in Casio's own format. The watch then shows tides accurate to about a minute, **fully offline**, on its stock screen (tide graph, high/low water, moon, sunrise/sunset). The firmware is not modified.

Our test case is **Saint-Malo, France**, with data from the French hydrographic office **SHOM**. The method works with any tide gauge or published constituents (see [other data sources](#other-data-sources-noaa-ukho-and-more)).

<p align="center">
  <img src="docs/img/montre_maree.jpg" width="340" alt="Casio G-Shock GBX-100 tide mode showing ST-MALO SHOM: high water 0:39 943 cm, low water 19:01 398 cm">
  <img src="docs/img/montre_heure.jpg" width="340" alt="Casio G-Shock GBX-100 main screen with the ST-MALO SHOM tide graph">
</p>

<p align="center"><em>The watch on 3 Oct 2026 after the upload. It shows low water at 19:01 (398 cm) and high water at 0:39 (943 cm). The official SHOM tide table gives 19:00 (4.00 m) and 00:40 (9.37 m).</em></p>

| Saint-Malo (vs gauge measurements, 2025) | Mean error on high/low water time | Max error |
|---|---|---|
| Casio's stock data (4 constituents) | 29 min | 2 h 05 |
| Our constants (60 constituents, SHOM gauge data) | 5 min | 24 min |
| Version aligned on the official SHOM table: watch vs table, 3 Oct 2026 | ≤ 1 min | — |

## Why Casio's stock data is not usable (at least in Saint-Malo)

![Saint-Malo: Casio stock data vs measurements vs our constants](docs/img/ecart_casio.png)

*Top: the tide on 3 October 2026. Casio's stock model gets the low waters roughly right but puts high water **43 minutes late**. Bottom: error on the time of 607 high and low waters (January–June 2025) against the **actual measurements** of the SHOM tide gauge. Those measurements were not used to fit our constants. Reproduce with `scripts/figure_ecart.py`.*

| Against measurements, Jan–Jun 2025 | Casio stock data | Our constants |
|---|---|---|
| Mean error on high/low water time | **29 min** | 5 min |
| Tides more than 30 min off | **44 %** | 0 % |
| Worst case | **2 h 05** | 24 min |

Why this makes the stock tide graph useless for actual sailing here:
- **The error is large and unpredictable.** It ranges from about −80 to +120 minutes depending on the day and on the point in the tidal cycle. A fixed mental correction cannot fix it: on the same day, low water can be right and high water 43 min late.
- **Time errors become height errors.** Saint-Malo's range reaches 12–13 m at springs. Around mid-tide the water moves by up to about 3 m per hour (rule of twelfths), so 30 minutes off can mean more than a metre of water. Over 2025 the stock model's height error averaged 50 cm, and reached 1.6 m.
- **The things that matter depend on the minute:** lock gates and harbour access timed on high water, drying moorings, sills and shallow passages, and the turn of the very strong tidal streams in the Gulf of Saint-Malo.

The cause is not the watch. It is the 4-constituent data set: Saint-Malo's tide is strongly distorted by shallow-water constituents (M4, MS4, MN4…) and the N2/K2 spring-neap modulation, none of which Casio sends. Ports elsewhere may be fine. Ports with large ranges or strongly non-sinusoidal tides are likely to show the same problem.

## The problem

For Saint-Malo, the Casio app only sends **4 harmonic constituents** (M2, S2, K1, O1, plus two tiny shallow-water terms). It leaves out N2 (0.71 m), K2 (0.41 m), M4, MS4 and others, which matters a lot at one of Europe's largest tidal ranges.

The watch firmware, however, **can compute tides from 60 constituents**: the app already uses that format for other ports (Japan, USA, part of France). All it needs is a correct set of 60 constants.

## Experimental approach

We worked through successive hypotheses, each checked against an independent source before moving on. We only touched the watch once the format was confirmed, and we started with a read-only connection.

**1. Static analysis of the app.** The CASIO WATCHES APK ships its tide-port databases in clear: about 3,300 ports (844 with 4 constituents, 2,492 with 60), with their harmonic constants. So the watch receives constants and does the computation itself. The order of the 60 columns is undocumented; we recovered it by recognising the main constituents of known ports.

**2. Quantify before touching anything.** We downloaded 7 years of hourly SHOM tide-gauge data for Saint-Malo and ran a harmonic analysis on 2019–2024. We then simulated both Casio's 4-constituent model and our 60-constituent model on 2025, held-out data. The expected gain was known before the first byte was sent.

**3. Follow the data path (decompilation for interoperability).** We decompiled the Flutter/Dart part with `blutter` and the native Android part with `jadx`. The Java layer builds a 1,009-byte binary block with 60 amplitudes and phases, sends it through a bulk Bluetooth transfer, then writes a small settings record.

**4. Ground truth from a Bluetooth capture.** We captured, with Apple's PacketLogger, the official iOS app sending a 60-constituent French port (La Rochelle). Our generator reproduces the captured block **byte for byte**, which confirmed units, conventions and the missing values (DST rule).

**5. Stepwise tests on the watch:** first a read-only connection from a Mac, then the upload, then a visual check on the watch against our predictions and the official tide table.

**6. Debug failures.** When the watch started rejecting transfers ("busy"), a second capture showed the full handshake that the app performs before each transfer. The script now replays it.

### Hypotheses confirmed or refuted

| Hypothesis | Result | Evidence |
|---|---|---|
| The watch computes tides itself from parameters | ✅ Confirmed | Harmonic constants in the APK; offline display |
| The inaccuracy comes from Casio's model, not the watch | ✅ Confirmed | Saint-Malo uses only 4 constituents; simulation shows ~30 min mean error |
| The firmware supports 60 constituents | ✅ Confirmed | 60-constituent ports in the app; our block displays correctly |
| The app only sends a port ID (database inside the watch) | ❌ Refuted | Java code + capture: the full constants block is transmitted |
| Units in cm and degrees; phases referenced to UTC; longitude positive West | ✅ Confirmed | Captured block reproduced byte for byte; correct times on the watch |
| 4-constituent ports use UTC+1 phases | ✅ Confirmed | Constant ~30° (one hour of M2) offset against our analysis and between neighbouring ports in both lists |
| A third-party client can write to the watch without pairing | ✅ Confirmed | Successful connection and upload from a Mac |
| The watch reloads data on every upload | ❌ Refuted | It only reloads when the port ID changes |
| The watch accepts a transfer at any time | ❌ Refuted | It refuses while showing tide mode, and without the app's handshake |
| The official tide table exactly matches the measurements | ❌ Refuted (at Saint-Malo) | The table is ~12 min earlier than our model; the measured tide lies in between |

The full protocol is documented in [docs/PROTOCOL.md](docs/PROTOCOL.md) (French version: [docs/PROTOCOLE.md](docs/PROTOCOLE.md)).

## Other watches than the GBX-100?

Tested **only on a GBX-100 (module 3482)**. Some leads for other models, **untested**:
- In the app code, module **3586** goes through the same "multi-slot" tide path as the 3482. It likely accepts the same format, but we have not verified it.
- The app also contains mapping tables for other tide-graph watches (modules 3452 and 5623, from the Rangeman and Frogman families). They seem to use different formats and exchanges. The same approach (APK analysis, then capture, then replay) should apply, but the code will need adapting.
- In version 4.6.0, the native Android side only enables tide transfers for the GBX-100.

If you try another model, start with `scripts/lecture_montre.py` (read-only) and capture the official app over Bluetooth to compare.

## Other data sources (NOAA, UKHO and more)

We used **SHOM** because the watch is used in Saint-Malo. The method is generic: any series of water levels covering at least a year, or published harmonic constituents, will do. Depending on where you sail:

| Region | Provider | What you get |
|---|---|---|
| France (incl. overseas) | **SHOM**, data.shom.fr (REFMAR) | Tide-gauge measurements, open licence |
| USA | **NOAA CO-OPS**, tidesandcurrents.noaa.gov | Measurements, plus **published harmonic constituents** (select "GMT" phases), so no analysis is needed |
| United Kingdom | **National Tidal and Sea Level Facility / BODC** | UK tide-gauge network data |
| Canada | **Fisheries and Oceans Canada / CHS** | Measurements, predictions |
| Germany, Netherlands, Belgium | **BSH**, **Rijkswaterstaat**, **Afdeling Kust** | National measurements and predictions |
| Spain, Portugal | **Puertos del Estado**, **Instituto Hidrográfico** | Port measurements |
| Australia, New Zealand | **Bureau of Meteorology**, **LINZ** | Measurements, predictions |
| Worldwide | **UHSLC**, **GESLA** | Tide-gauge series from around the world |
| Anywhere, even without a gauge | Global models **FES2022** (AVISO), **TPXO** | Constituents at any point; less accurate near coasts and in estuaries |

Whatever the source, check that:
- phases are **Greenwich/UTC-referenced** (not local time) and amplitudes are in **cm**;
- constituent names are mapped to Casio's order (done in `constantes_casio.py`);
- the height datum (local chart datum or mean sea level) suits you, since it sets the displayed heights;
- if you want to match your official local tide table rather than the measurements, you calibrate a time offset as in `aligne_shom.py`.

## Usage

Requirements: Python 3.10+ and a computer with Bluetooth LE. Tested on macOS 26 (Apple Silicon). Script comments and messages are in French.

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```

Run all commands from the repository root.

### Upload Saint-Malo tides (constants included)

1. Turn off Bluetooth on the phone paired with the watch, otherwise it will grab the connection.
2. Put the watch on the **time screen**. In tide mode it refuses the transfer.
3. Run the command, then press the watch's connect button:

```bash
python scripts/envoi_maree.py data/saint_malo_3482_shom.bin
```

The watch should then show "ST-MALO SHOM" in tide mode. Use `data/saint_malo_3482.bin` for the version fitted on measurements rather than on the official table. The script also sets the watch time from the computer.

To read the tide settings only, without writing anything:

```bash
python scripts/lecture_montre.py
```

### Recompute the constants, or compute them for another port

```bash
python scripts/telecharger_refmar.py 410 2019 2025 data/saint_malo_horaire.csv
python scripts/analyse.py
python scripts/constantes_casio.py
python scripts/gen_blob.py
python scripts/aligne_shom.py
python scripts/previsions.py 2026-10-03
```

What each step does:
- `telecharger_refmar.py` downloads SHOM gauge data (410 = Saint-Malo). For other providers, produce a CSV with columns `t` (UTC) and `h` (metres).
- `analyse.py` runs the harmonic analysis and compares it with Casio's model.
- `constantes_casio.py` writes the constants in Casio's format. Name, latitude and longitude can be passed as arguments.
- `gen_blob.py` builds the 1,009-byte block. The displayed name is at most 18 characters.
- `aligne_shom.py` is optional: it applies the time offset towards the official table and checks the result.
- `previsions.py` prints predicted high/low waters, to compare with the watch.
- `figure_ecart.py` draws the Casio vs measurements vs our constants comparison chart.

Bonus: `parse_pklg.py` decodes a PacketLogger (macOS/iOS) Bluetooth capture into a list of GATT operations.

## Limitations and caveats

- **Personal project, not affiliated with Casio or SHOM.** Use at your own risk. The worst case we hit was reversible: selecting a port again in the CASIO WATCHES app restores the stock data.
- **The Casio app may overwrite the data.** On each reconnection it re-sends its own data for the stored port ID. The script uses an ID the app does not know (9999 or 9998) to avoid this. Persistence over several days is still to be confirmed.
- This is **not a navigation instrument**. Predictions do not include weather effects (storm surges of 10–20 cm are common). Always refer to official publications.

## Sources, licences and credits

- **Tide-gauge data:** © SHOM, REFMAR network, [data.shom.fr](https://data.shom.fr), [Etalab Open Licence 2.0](https://www.etalab.gouv.fr/licence-ouverte-open-licence/). The raw data is not included; `telecharger_refmar.py` downloads it. The constants in `data/` are derived from it.
- **Protocol:** determined by analysing the CASIO WATCHES 4.6.0 app, solely for interoperability (EU Directive 2009/24/EC, Art. 6), and confirmed with Bluetooth captures. This repository contains no Casio code or files; only Casio's 6 Saint-Malo constants are quoted in `analyse.py`, for comparison. The [Gadgetbridge](https://gadgetbridge.org) project's reverse engineering of Casio watches was the starting point.
- **Tools:** [utide](https://github.com/wesleybowman/UTide), [bleak](https://github.com/hbldh/bleak), [blutter](https://github.com/worawit/blutter), [jadx](https://github.com/skylot/jadx), PacketLogger (Apple).
- **Code:** MIT licence (see [LICENSE](LICENSE)).

*Keywords: Casio G-Shock GBX-100 tide graph accuracy, wrong tide times, custom tide port, harmonic constituents, tide prediction, Bluetooth LE protocol, CASIO WATCHES app, G-SHOCK MOVE, NOAA, SHOM, UKHO.*
