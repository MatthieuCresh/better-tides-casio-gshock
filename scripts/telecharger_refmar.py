"""Télécharge les hauteurs d'eau horaires validées (source 4) d'un marégraphe SHOM / REFMAR.
Par défaut : Saint-Malo (id 410), 2019 à 2025.
Données : SHOM, réseau REFMAR — Licence Ouverte Etalab (https://data.shom.fr).
Usage : python scripts/telecharger_refmar.py [id_maregraphe] [annee_debut] [annee_fin] [sortie.csv]"""
import json, sys, urllib.request
import pandas as pd

ID   = int(sys.argv[1]) if len(sys.argv) > 1 else 410
Y0   = int(sys.argv[2]) if len(sys.argv) > 2 else 2019
Y1   = int(sys.argv[3]) if len(sys.argv) > 3 else 2025
OUT  = sys.argv[4] if len(sys.argv) > 4 else 'data/saint_malo_horaire.csv'
API  = 'https://services.data.shom.fr/maregraphie/observation/json/{id}?sources=4&dtStart={a}&dtEnd={b}'

rows = []
for y in range(Y0, Y1 + 1):
    for m in range(1, 13):                     # l'API limite la taille des réponses : un mois par requête
        a = f'{y}-{m:02d}-01T00:00:00Z'
        b = f'{y + (m == 12)}-{m % 12 + 1:02d}-01T00:00:00Z'
        data = json.load(urllib.request.urlopen(API.format(id=ID, a=a, b=b), timeout=60))['data']
        rows += [(r['timestamp'], r['value']) for r in data]
    print(y, 'ok')
df = pd.DataFrame(rows, columns=['t', 'h'])
df['t'] = pd.to_datetime(df.t, format='%Y/%m/%d %H:%M:%S', utc=True)
df = df.drop_duplicates('t').sort_values('t')
df.to_csv(OUT, index=False)
print(f'{len(df)} mesures ({df.t.min()} -> {df.t.max()}) écrites dans {OUT}')
