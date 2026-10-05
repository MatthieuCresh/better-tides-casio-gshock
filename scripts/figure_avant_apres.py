"""Image « avant / après » pour présenter le projet (docs/img/avant_apres.png).
Avant : modèle Casio d'origine (4 ondes) face aux mesures du marégraphe, le 3 octobre 2026.
Après : photo de la montre avec nos constantes. Chiffres issus de figure_ecart.py (janvier-juin 2025).
Usage : python scripts/figure_avant_apres.py   (nécessite data/saint_malo_horaire.csv)"""
import copy, json, urllib.request, warnings
import numpy as np, pandas as pd, utide
import matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt, matplotlib.dates as mdates
from PIL import Image
warnings.filterwarnings('ignore')

RED, BLUE, GREY, INK = '#c62828', '#1565c0', '#9e9e9e', '#212121'
LAT = 48.6408
df = pd.read_csv('data/saint_malo_horaire.csv', parse_dates=['t']); t = df.t.dt.tz_convert(None)
train = t < '2025-01-01'
CASIO = {'M2': (207, 3.69), 'S2': (259, 1.43), 'K1': (112, 0.10), 'O1': (359, 0.08), 'M4': (286, 0.017), 'M6': (164, 0.0)}
casio = utide.solve(t[train], df.h[train].values, lat=LAT, constit=list(CASIO), method='ols',
                    conf_int='none', trend=False, verbose=False)
casio['A'] = np.array([CASIO[n][1] for n in casio.name])
casio['g'] = np.array([(CASIO[n][0] - 360 * f) % 360 for n, f in zip(casio.name, casio.aux.frq)])
casio['mean'] = 6.78

day = pd.date_range('2026-10-03 07:00', '2026-10-03 15:00', freq='2min')        # UTC (09:00-17:00 Paris)
loc = lambda x: x.tz_localize('UTC').tz_convert('Europe/Paris').tz_localize(None)
url = ('https://services.data.shom.fr/maregraphie/observation/json/410?sources=1'
       '&dtStart=2026-10-03T07:00:00Z&dtEnd=2026-10-03T15:00:00Z')
d = json.load(urllib.request.urlopen(url, timeout=120))['data']
obs = pd.Series({pd.Timestamp(r['timestamp']): r['value'] for r in d}).sort_index().rolling(11, center=True).mean()
pc = utide.reconstruct(day, casio, verbose=False).h

fig = plt.figure(figsize=(16, 9), dpi=110, facecolor='white')
fig.text(.5, .94, "My G-Shock's tide times were up to 2 hours off. Now they're within a minute.",
         ha='center', fontsize=25, weight='bold', color=INK)
fig.text(.5, .895, 'Casio GBX-100 · Saint-Malo, France (12 m tidal range) · checked against the official SHOM tide gauge',
         ha='center', fontsize=13.5, color='#616161')

# --- AVANT ---
fig.text(.27, .82, 'BEFORE', ha='center', fontsize=20, weight='bold', color=RED)
fig.text(.27, .785, "Casio's stock data (4 tidal components)", ha='center', fontsize=13.5, color=INK)
ax = fig.add_axes([.07, .30, .40, .44])
ax.plot(loc(obs.index), obs.values, color=GREY, lw=5, label='Real tide (gauge)', solid_capstyle='round')
ax.plot(loc(day), pc, color=RED, lw=2.5, ls='--', label="Casio's model (recomputed)")
hw_obs = loc(pd.DatetimeIndex([obs.idxmax()]))[0]; hw_c = loc(pd.DatetimeIndex([day[np.argmax(pc)]]))[0]
y = 10.45
ax.annotate('', xy=(hw_c, y), xytext=(hw_obs, y), arrowprops=dict(arrowstyle='<->', color=RED, lw=2))
ax.text(hw_obs + (hw_c - hw_obs) / 2, y + .12, f'high water {int((hw_c - hw_obs).total_seconds() // 60)} min late',
        ha='center', fontsize=12.5, color=RED, weight='bold')
ax.set_ylim(5.5, 11); ax.set_ylabel('Water height (m)', fontsize=11)
ax.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M')); ax.tick_params(labelsize=10)
ax.legend(loc='lower center', fontsize=11, frameon=False, ncol=2)
for s in ('top', 'right'): ax.spines[s].set_visible(False)
ax.set_title('3 October 2026', fontsize=11.5, color='#616161', loc='left')
fig.text(.27, .19, '29 min', ha='center', fontsize=40, weight='bold', color=RED)
fig.text(.27, .15, 'average error on high/low water · up to 2 h 05', ha='center', fontsize=13, color=INK)
fig.text(.27, .12, '(607 tides, Jan–Jun 2025, vs tide-gauge measurements)', ha='center', fontsize=10.5, color='#757575')

# --- APRÈS ---
fig.text(.73, .82, 'AFTER', ha='center', fontsize=20, weight='bold', color=BLUE)
fig.text(.73, .785, '60 components fitted on 7 years of tide-gauge data', ha='center', fontsize=13.5, color=INK)
img = Image.open('docs/img/montre_maree.jpg')
w, h = img.size; img = img.crop((int(w * .12), int(h * .30), int(w * .88), int(h * .80)))   # cadrage sur le cadran
axi = fig.add_axes([.555, .25, .35, .52]); axi.imshow(img); axi.axis('off')
fig.text(.73, .19, '≤ 1 min', ha='center', fontsize=40, weight='bold', color=BLUE)
fig.text(.73, .15, 'vs the official tide table, on the watch (19:01 vs 19:00, 0:39 vs 00:40)', ha='center', fontsize=13, color=INK)
fig.text(.73, .12, '(5 min average vs tide-gauge measurements, Jan–Jun 2025)', ha='center', fontsize=10.5, color='#757575')

fig.add_artist(plt.Line2D([.5, .5], [.12, .82], color='#e0e0e0', lw=1.5))
fig.patches.append(matplotlib.patches.Rectangle((0, 0), 1, .075, transform=fig.transFigure, color=INK, zorder=-1))
fig.text(.5, .032, 'No firmware mod  ·  Stock screen  ·  Fully offline  ·  Open source',
         ha='center', fontsize=17, weight='bold', color='white')
fig.text(.985, .012, 'github.com/MatthieuCresh/better-tides-casio-gshock', ha='right', fontsize=9.5, color='#bdbdbd')
fig.savefig('docs/img/avant_apres.png', facecolor='white')
print('écrit : docs/img/avant_apres.png')
