"""Convertit les constantes harmoniques (sortie de analyse.py) au format « 60 composantes » attendu par la GBX-100 :
ordre des 60 ondes de la liste japonaise, amplitudes et Z0 en cm, phases en degrés (référence UTC).
Usage : python scripts/constantes_casio.py [constantes.json] [sortie.csv] [nom] [lat] [lon_est] [graph_pattern]
  graph_pattern : échelle verticale du graphe de marée sur la montre (ex. « 8D »). Par défaut, choisie automatiquement
  d'après le marnage (voir GRAPH_SCALE) ; pour un port proche d'un port Casio, reprendre sa valeur donne le même rendu."""
import json, sys
import numpy as np

SRC  = sys.argv[1] if len(sys.argv) > 1 else 'data/saint_malo_60.json'
OUT  = sys.argv[2] if len(sys.argv) > 2 else 'data/saint_malo_format_casio60.csv'
NAME = sys.argv[3] if len(sys.argv) > 3 else 'SAINT-MALO (SHOM)'
LAT  = float(sys.argv[4]) if len(sys.argv) > 4 else 48.6408
LON  = float(sys.argv[5]) if len(sys.argv) > 5 else -2.0281      # Est positif
GRAPH = sys.argv[6] if len(sys.argv) > 6 else ('2B' if len(sys.argv) <= 1 else 'auto')   # 2B : valeur Casio de Saint-Malo

# Échelle du graphe : le nombre du « graph pattern » diminue quand le marnage augmente. Valeurs médianes de
# 2 x (somme des amplitudes, cm) observées pour chaque nombre dans la base Casio des 2 492 ports à 60 ondes.
GRAPH_SCALE = {3: 1248, 4: 1167, 5: 956, 6: 919, 7: 808, 8: 772, 9: 581, 10: 457, 11: 336, 12: 219, 13: 96, 14: 12}

# Ordre des 60 ondes dans le format Casio (liste japonaise standard) et noms correspondants dans utide
CASIO = ("Sa Ssa Mm MSf Mf 2Q1 SIG1 Q1 RHO1 O1 MP1 M1 CHI1 PI1 P1 S1 K1 PSI1 PHI1 THE1 J1 SO1 OO1 OQ2 MNS2 2N2 MU2 "
         "N2 NU2 OP2 M2 MKS2 LDA2 L2 T2 S2 R2 K2 MSN2 KJ2 2SM2 MO3 M3 SO3 MK3 SK3 MN4 M4 SN4 MS4 MK4 S4 SK4 2MN6 M6 "
         "MSN6 2MS6 2MK6 2SM6 MSK6").split()
UT = {'Sa': 'SA', 'Ssa': 'SSA', 'Mm': 'MM', 'MSf': 'MSF', 'Mf': 'MF', 'M1': 'NO1'}

d = json.load(open(SRC))
m = {n: (a, g) for n, a, g in zip(d['name'], d['A'], d['g'])}
get = lambda c: m.get(UT.get(c, c.upper()), (0, 0))      # ondes absentes de l'analyse (MP1, MNS2, KJ2) -> 0
A = [round(get(c)[0] * 100, 1) for c in CASIO]
P = [round(get(c)[1]) for c in CASIO]

hdr = (['List_No', 'ID', 'PortName', 'Latitude', 'Longitude', 'Z0', 'TimeDiff', 'DSTRule', 'GraphPattern', 'HcA']
       + [str(i) for i in range(1, 60)] + ['HcP'] + [str(i) for i in range(1, 60)]
       + ['HcT', 'LongitudeApp', 'Country', 'Area'])
# HcT 7 : valeur de tous les ports français et canadiens de la base Casio (sens exact inconnu)
if GRAPH == 'auto':      # lettre : sens inconnu, « E » est la plus fréquente dans la base Casio
    amp2 = 2 * sum(A)
    GRAPH = f"{min(GRAPH_SCALE, key=lambda k: abs(np.log(GRAPH_SCALE[k]) - np.log(max(amp2, 1))))}E"
    print(f'graph pattern choisi d\'après le marnage ({amp2/100:.1f} m) : {GRAPH}')
row = (['2', '99999', NAME, f'{LAT:+.4f}', f'{-LON:+.4f}', round(d['Z0'] * 100, 1), '1', '', GRAPH]
       + A + P + ['7', f'{LON:+.4f}', 'FRANCE', 'EUROPE'])
with open(OUT, 'w') as f:
    f.write(','.join(hdr) + '\n' + ','.join(map(str, row)) + '\n')
print('écrit :', OUT)
