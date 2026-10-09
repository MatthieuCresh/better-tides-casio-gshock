"""Figure « pourquoi les données Casio d'origine ne sont pas exploitables » (docs/img/ecart_casio.png).
1) Courbe du 3 octobre 2026 : mesures du marégraphe, modèle Casio d'origine, nos constantes, annuaire SHOM.
2) Erreur sur l'heure des PM/BM face aux mesures (janvier-juin 2025, données 10 min non utilisées pour l'ajustement).
Usage : python scripts/figure_ecart.py   (nécessite data/saint_malo_horaire.csv, voir telecharger_refmar.py)"""
import copy, json, urllib.request, warnings
import numpy as np, pandas as pd, utide
import matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt
warnings.filterwarnings('ignore')
LAT, API = 48.6408, 'https://services.data.shom.fr/maregraphie/observation/json/410?sources={s}&dtStart={a}&dtEnd={b}'

def shom(src, a, b):
    d = json.load(urllib.request.urlopen(API.format(s=src, a=a, b=b), timeout=120))['data']
    s = pd.Series({pd.Timestamp(r['timestamp']): r['value'] for r in d}).sort_index()
    return s[~s.index.duplicated()]

df = pd.read_csv('data/saint_malo_horaire.csv', parse_dates=['t']); t = df.t.dt.tz_convert(None)
names = json.load(open('data/saint_malo_60.json'))['name']
fit = lambda m, const: utide.solve(t[m], df.h[m].values, lat=LAT, constit=const, method='ols',
                                   conf_int='none', trend=False, verbose=False)
train = t < '2025-01-01'
ours = fit(train, names)                                   # nos 60 ondes (ajustées 2019-2024)
# modèle Casio d'origine : 6 constantes de l'appli pour Saint-Malo (phases en UTC+1, ramenées en UTC)
CASIO = {'M2': (207, 3.69), 'S2': (259, 1.43), 'K1': (112, 0.10), 'O1': (359, 0.08), 'M4': (286, 0.017), 'M6': (164, 0.0)}
casio = fit(train, list(CASIO))
casio['A'] = np.array([CASIO[n][1] for n in casio.name])
casio['g'] = np.array([(CASIO[n][0] - 360 * f) % 360 for n, f in zip(casio.name, casio.aux.frq)])
casio['mean'] = 6.78
pred = lambda c, tt: utide.reconstruct(tt, c, verbose=False).h

def extrema(times, h):
    out = []
    for i in range(4, len(h) - 4):
        w = h[i-4:i+5]
        if np.isnan(w).any() or not (h[i] == w.max() or h[i] == w.min()): continue
        dtm = (times[1] - times[0]).total_seconds() / 60
        c = np.polyfit(np.arange(-4, 5) * dtm, w, 2); x = -c[1] / (2 * c[0])
        if abs(x) <= dtm: out.append((times[i] + pd.Timedelta(minutes=x), 'HW' if c[0] < 0 else 'LW'))
    return out

fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(9, 8.5), gridspec_kw={'height_ratios': [1.15, 1]})

# --- 1. le 3 octobre 2026 ---
day = pd.date_range('2026-10-02 22:00', '2026-10-03 22:00', freq='5min')   # UTC = 00:00-24:00 heure de Paris
loc = lambda x: x.tz_localize('UTC').tz_convert('Europe/Paris').tz_localize(None)
obs = shom(1, '2026-10-02T22:00:00Z', '2026-10-03T22:00:00Z').rolling(11, center=True).mean()
ax1.plot(loc(obs.index), obs.values, color='0.55', lw=3, label='Measured (SHOM tide gauge)')
ax1.plot(loc(day), pred(casio, day), color='#d62728', lw=1.8, ls='--', label='Casio stock data (4 constituents)')
ax1.plot(loc(day), pred(ours, day), color='#1f77b4', lw=1.8, label='Our constants (60 constituents)')
annuaire = [('06:30', 3.70), ('12:00', 10.11), ('19:00', 4.00)]
ax1.scatter([pd.Timestamp(f'2026-10-03 {h}') for h, _ in annuaire], [v for _, v in annuaire], zorder=5,
            color='k', marker='D', s=30, label='Official SHOM tide table')
ax1.annotate('Casio: high water\n43 min late', xy=(pd.Timestamp('2026-10-03 12:43'), 10.07),
             xytext=(pd.Timestamp('2026-10-03 14:40'), 9.9), color='#d62728', fontsize=9,
             arrowprops=dict(arrowstyle='->', color='#d62728'))
ax1.set_title('Saint-Malo, 3 October 2026 (local time)', fontsize=11, loc='left', pad=48)
ax1.set_ylabel('Height above chart datum (m)'); ax1.grid(alpha=.3); ax1.legend(fontsize=8.5, loc='lower center', bbox_to_anchor=(0.5, 1.07), ncol=2, frameon=False)
ax1.xaxis.set_major_formatter(matplotlib.dates.DateFormatter('%H:%M'))

# --- 2. erreurs face aux mesures, janvier-juin 2025 ---
s = pd.concat([shom(3, f'2025-{m:02d}-01T00:00:00Z', f'2025-{m+1:02d}-01T00:00:00Z') for m in range(1, 7)])
s = s[~s.index.duplicated()]
full = pd.date_range(s.index.min(), s.index.max(), freq='10min')
o = s.reindex(full).interpolate(limit=3).values
fine = pd.date_range(full[0], full[-1], freq='2min')
eo = extrema(full, o)
errs = {}
for lab, c in [('Casio stock data', casio), ('Our constants', ours)]:
    ep = extrema(fine, pred(c, fine)); pt = np.array([e[0].value for e in ep])
    e = []
    for tm, k in eo:
        j = np.argmin(abs(pt - tm.value))
        if ep[j][1] == k and abs(pt[j] - tm.value) < 150 * 60e9: e.append((pt[j] - tm.value) / 60e9)
    errs[lab] = np.array(e)
bins = np.arange(-120, 125, 5)
ax2.hist(errs['Casio stock data'], bins, color='#d62728', alpha=.6, label='Casio stock data')
ax2.hist(errs['Our constants'], bins, color='#1f77b4', alpha=.75, label='Our constants')
for lab, col, y in [('Casio stock data', '#d62728', .92), ('Our constants', '#1f77b4', .85)]:
    e = errs[lab]
    ax2.text(.99, y, f'{lab}: mean |error| {np.abs(e).mean():.0f} min, '
             f'{(np.abs(e) > 30).mean()*100:.0f}% over 30 min, max {np.abs(e).max():.0f} min',
             transform=ax2.transAxes, ha='right', color=col, fontsize=9)
ax2.set_title(f'High/low water time error vs measurements, Jan–Jun 2025 ({len(eo)} tides)', fontsize=11, loc='left')
ax2.set_xlabel('Predicted minus measured (minutes)'); ax2.set_ylabel('Number of tides'); ax2.grid(alpha=.3)
ax2.legend(fontsize=8.5, loc='upper left')
fig.tight_layout(); fig.savefig('docs/img/ecart_casio.png', dpi=130)
for k, e in errs.items():
    print(f'{k}: n={len(e)} |err| moyen {np.abs(e).mean():.1f} min, >30 min {(np.abs(e)>30).mean()*100:.0f} %, max {np.abs(e).max():.0f} min')
