"""Convertit les constantes harmoniques (sortie de analyse.py) au format « 60 composantes » attendu par la GBX-100 :
ordre des 60 ondes de la liste japonaise, amplitudes et Z0 en cm, phases en degrés (référence UTC).
Usage : python scripts/constantes_casio.py [constantes.json] [sortie.csv] [nom] [lat] [lon_est]"""
import json, sys

SRC  = sys.argv[1] if len(sys.argv) > 1 else 'data/saint_malo_60.json'
OUT  = sys.argv[2] if len(sys.argv) > 2 else 'data/saint_malo_format_casio60.csv'
NAME = sys.argv[3] if len(sys.argv) > 3 else 'SAINT-MALO (SHOM)'
LAT  = float(sys.argv[4]) if len(sys.argv) > 4 else 48.6408
LON  = float(sys.argv[5]) if len(sys.argv) > 5 else -2.0281      # Est positif

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
# GraphPattern "2B" et HcT 7 : valeurs utilisées par Casio pour Saint-Malo / les ports français (sens exact inconnu)
row = (['2', '99999', NAME, f'{LAT:+.4f}', f'{-LON:+.4f}', round(d['Z0'] * 100, 1), '1', '', '2B']
       + A + P + ['7', f'{LON:+.4f}', 'FRANCE', 'EUROPE'])
with open(OUT, 'w') as f:
    f.write(','.join(hdr) + '\n' + ','.join(map(str, row)) + '\n')
print('écrit :', OUT)
