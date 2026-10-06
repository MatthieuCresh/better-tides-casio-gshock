"""Génère le bloc de 1009 octets (format Casio « 60 composantes », module 3482 / GBX-100).
Format décrit dans docs/PROTOCOLE.md, vérifié octet par octet sur une capture Bluetooth de l'appli officielle.
Usage : python scripts/gen_blob.py [constantes.csv] [sortie.bin] [nom affiché] [fuseau_heures] [regle_heure_ete]
  fuseau : décalage UTC en heures, hors heure d'été (France : 1 ; Vancouver : -8)
  règle d'heure d'été : 2 = Union européenne (confirmé) ; autres régions : code inconnu à ce jour"""
import csv, struct, sys

def make_blob(name, lat, lon_east, z0_cm, graph, amps_cm, phases_deg, tz_min=60, dst_diff_min=60, dst_rule=2, hct=7):
    b = bytearray(1009)
    b[0] = 2                                           # ListNo = 60 composantes
    n = name.encode()[:18]; b[1:1+len(n)] = n
    struct.pack_into('<dd', b, 19, lat, -lon_east)     # longitude : convention montre, Ouest positif
    struct.pack_into('<bbB', b, 35, tz_min//15, dst_diff_min//15, dst_rule)   # 2 = règle heure d'été UE
    struct.pack_into('<d', b, 38, z0_cm)
    struct.pack_into('<H', b, 46, graph)
    struct.pack_into('<60d', b, 48, *amps_cm)
    struct.pack_into('<60d', b, 528, *phases_deg)      # degrés, référence UTC (Greenwich)
    b[1008] = hct
    return bytes(b)

def graph_code(s):                                     # "7C" -> 73, "2B" -> 22
    return int(''.join(str(ord(c)-64) if c.isalpha() else c for c in s))

def from_casio_row(h, r, name=None, lat=None, lon_east=None, tz_hours=1.0, dst_rule=2):
    """Construit le bloc à partir d'une ligne au format CSV « 60 composantes » (voir constantes_casio.py)."""
    ia, ip = h.index('HcA'), h.index('HcP')
    f = lambda x: float(x or 0)
    return make_blob(name or r[2], lat if lat is not None else f(r[3]),
                     lon_east if lon_east is not None else -f(r[4]),
                     f(r[5]), graph_code(r[8]), [f(x) for x in r[ia:ia+60]], [f(x) for x in r[ip:ip+60]],
                     tz_min=int(round(tz_hours * 60)), dst_rule=dst_rule, hct=int(r[h.index('HcT')]))

if __name__ == '__main__':
    src = sys.argv[1] if len(sys.argv) > 1 else 'data/saint_malo_format_casio60.csv'
    out = sys.argv[2] if len(sys.argv) > 2 else 'data/saint_malo_3482.bin'
    name = sys.argv[3] if len(sys.argv) > 3 else 'ST-MALO SHOM'
    tz = float(sys.argv[4]) if len(sys.argv) > 4 else 1.0
    rule = int(sys.argv[5]) if len(sys.argv) > 5 else 2
    h, r = list(csv.reader(open(src)))[:2]
    blob = from_casio_row(h, r, name=name, lat=float(r[3]), lon_east=-float(r[4]), tz_hours=tz, dst_rule=rule)
    open(out, 'wb').write(blob)
    print(f'{out} : {len(blob)} octets ; en-tête {blob[:48].hex(" ")}')
