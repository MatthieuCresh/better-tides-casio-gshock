# Bluetooth LE tide-data protocol — Casio G-Shock GBX-100 (module 3482)

*[Version française](PROTOCOLE.md)*

This description comes from analysing the CASIO WATCHES 4.6.0 app (Android). It was confirmed by Bluetooth captures between the iOS app and a GBX-100, then by successful uploads from `scripts/envoi_maree.py`.

Legend: ✅ = confirmed (capture or successful upload), ℹ️ = inferred, ❓ = unknown.

## 1. GATT characteristics

Casio service `26eb000d-b012-49a8-b1f8-394fb2032b0f`. Characteristics have the form `26eb00XX-b012-49a8-b1f8-394fb2032b0f`.

| UUID | Role | Properties |
|---|---|---|
| `26eb002c` | Read requests `[class, options…]` | write without response |
| `26eb002d` | Setting writes `[class, data…]`; replies to reads | write, notify |
| `26eb0023` | "Convoy" bulk-transfer control (DRSP) | write, notify |
| `26eb0024` | "Convoy" bulk-transfer data | write without response, notify |

Frames on `26eb002d` are limited to 20 bytes. Tide data uses **class `0x2E`**: frame `[0x2E, unit, ≤ 18 bytes]`.

| Unit | Content |
|---|---|
| 2 | Tide settings (6 bytes) ✅ |
| 3, 4, 5 | "User" points 1–3 (manually entered high-water time, position) ✅ |

To read a unit, write `2E <unit>` to `26eb002c`. The reply `2E <unit> <data>` arrives as a notification on `26eb002d`.

## 2. Tide settings (unit 2) ✅

| Byte | Content |
|---|---|
| 0 | Active slot: 0 = preset, 1–3 = user points, **4 = APP** (data sent by the phone) |
| 1–2 | Preset port ID (uint16 LE) |
| 3–4 | APP port ID (uint16 LE) |
| 5 | bit 0: display in feet |

Example: `04 b6 07 6b 02 00` means slot APP, preset port 1974, APP port 619 (Casio's Saint-Malo).

- ℹ️ If the APP port ID does not change, the watch **does not reload** a newly uploaded block. The script therefore alternates between 9999 and 9998.
- ℹ️ On every reconnection, the official app reads unit 2. If the slot is APP, it re-sends its own data for that ID, provided the ID is in its database.

## 3. The "60-constituent" tide block (1,009 bytes) ✅

All numbers are little-endian.

| Offset | Size | Field |
|---|---|---|
| 0 | 1 | List type: **2** = 60 constituents |
| 1 | 18 | Displayed name, UTF-8, zero-padded |
| 19 | 8 | Latitude, double, degrees (North positive) |
| 27 | 8 | Longitude, double, degrees, **West positive** |
| 35 | 1 | Time zone in quarter hours (int8): 4 = UTC+1 |
| 36 | 1 | DST offset in quarter hours: 4 = 1 h |
| 37 | 1 | DST rule: **2 = European Union** |
| 38 | 8 | Z0 (mean level above chart datum), double, **cm** |
| 46 | 2 | "Graph pattern" (uint16) ❓. Alphanumeric code where A–I map to 1–9: "2B" = 22, "7C" = 73 |
| 48 | 480 | 60 amplitudes, doubles, **cm** |
| 528 | 480 | 60 phases, doubles, **degrees, UTC (Greenwich) reference** |
| 1008 | 1 | "HcT" ❓ (7 for French ports) |

**Order of the 60 constituents** (standard Japanese list):
Sa, Ssa, Mm, MSf, Mf, 2Q1, σ1, Q1, ρ1, **O1**, MP1, M1, χ1, π1, **P1**, S1, **K1**, ψ1, φ1, θ1, J1, SO1, OO1, OQ2, MNS2, 2N2, μ2, **N2**, ν2, OP2, **M2**, MKS2, λ2, L2, T2, **S2**, R2, **K2**, MSN2, KJ2, 2SM2, MO3, M3, SO3, MK3, SK3, MN4, **M4**, SN4, **MS4**, MK4, S4, SK4, 2MN6, M6, MSN6, 2MS6, 2MK6, 2SM6, MSK6.

There is also a 163-byte "4-constituent" format (list type 1: M2, S2, K1, O1 plus two shallow-water terms, as scaled integers). The app uses it for Saint-Malo. It is not used here.

## 4. Upload sequence ✅

Connections that skip the handshake sometimes work, but the watch often answers "busy". The full sequence below, which is the app's, has always worked.

**1. Handshake** on `26eb002c` (read) and `26eb002d` (write). "Echo" means read the value, then write it back unchanged:
- reads `22`, `10`;
- write the name `23 "CASIO GBX-100"` (18 bytes);
- echoes `11`, `3B`, `3A`;
- reads `26`, `28`, `20`, `28`;
- echoes `1D`, `1E 00`, `1E 01`, `1F 00`, `1F 01`, `2F`, `45`, `2E 02`;
- **set the time**: `09 <year u16> <month> <day> <h> <min> <s> <weekday, Sunday = 0> <1/256 s> 01`;
- read `28`.

**2. Watch requests.** The watch notifies `47 01`. Reply `13`, then `5A FF`, then do two small transfers: category `0x11` (watch to phone) and `3D 30`, then category `0x32` (`00 32 00 00 00 01 00`, closed with `04 32`). Finally, read units 2 to 5.

**3. Block transfer.** Notifications on `26eb0023` and `26eb0024` are **enabled at the start of each transfer and disabled at the end**.
1. Write `00 23 F1 03 00` to `26eb0023` (start, category 0x23, length 1,009).
2. The watch notifies on `26eb0024`:
   - `00 00 00` if it is ready. Otherwise `00 01 <reason>` (1 low battery, 2 low temperature, 3 memory, **4 busy**, 7 preparing). In that case, send `03 00` on `26eb0024` to abort, then retry;
   - then `02 <MTU u16>`, for example `02 b9 00` for an MTU of 185.
3. Send the block as `05 <MTU − 4 bytes>` packets on `26eb0024`, write without response, about 0.4 s apart. There is no CRC and no header.
4. The watch notifies `04 23 …` on `26eb0023`. Reply `04 23`.

**4. Activation.** Write `2E 02 <settings>` to `26eb002d` with slot = 4 and an APP port ID **different** from the current one.

The watch also refuses the transfer ("busy") while it is **displaying tide mode**.

## 5. Open questions

- Exact meaning of "graph pattern" and "HcT".
- Whether the data persists through the official app's automatic reconnections.
- Detailed format of the user points (units 3–5).
- Behaviour of other modules (3586, 3452, 5623…).
