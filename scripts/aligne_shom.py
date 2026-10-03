"""Décale toutes les phases pour avancer la marée de DT minutes (alignement sur l'annuaire SHOM),
vérifie sur les marées de l'annuaire, puis génère data/saint_malo_3482_shom.bin."""
import csv, json, copy, numpy as np, pandas as pd, utide, warnings
from utide._ut_constants import ut_constants
import sys, os; sys.path.insert(0, os.path.dirname(__file__))
from gen_blob import from_casio_row
warnings.filterwarnings('ignore')
DT = 12.0  # minutes
CASIO="Sa Ssa Mm MSf Mf 2Q1 SIG1 Q1 RHO1 O1 MP1 M1 CHI1 PI1 P1 S1 K1 PSI1 PHI1 THE1 J1 SO1 OO1 OQ2 MNS2 2N2 MU2 N2 NU2 OP2 M2 MKS2 LDA2 L2 T2 S2 R2 K2 MSN2 KJ2 2SM2 MO3 M3 SO3 MK3 SK3 MN4 M4 SN4 MS4 MK4 S4 SK4 2MN6 M6 MSN6 2MS6 2MK6 2SM6 MSK6".split()
UT={'Sa':'SA','Ssa':'SSA','Mm':'MM','MSf':'MSF','Mf':'MF','M1':'NO1'}
frq=dict(zip(ut_constants.const.name, ut_constants.const.freq))   # cycles/heure
rows=list(csv.reader(open('data/saint_malo_format_casio60.csv'))); h,r=rows[0],list(rows[1])
ip=h.index('HcP')
for i,c in enumerate(CASIO):
    f=frq.get(UT.get(c,c.upper()))
    if f is not None: r[ip+i]=str(round((float(r[ip+i]) - 360*f*DT/60) % 360, 2))
with open('data/saint_malo_format_casio60_shom.csv','w') as fo: fo.write(','.join(h)+'\n'+','.join(r)+'\n')
blob=from_casio_row(h, r, name='ST-MALO SHOM', lat=48.6408, lon_east=-2.0281)
open('data/saint_malo_3482_shom.bin','wb').write(blob)

# vérification : prévision avec les constantes décalées vs annuaire
df=pd.read_csv('data/saint_malo_horaire.csv',parse_dates=['t']); t=df.t.dt.tz_convert(None)
names=json.load(open('data/saint_malo_60.json'))['name']
coef=utide.solve(t,df.h.values,lat=48.6408,constit=names,method='ols',conf_int='none',trend=False,verbose=False)
c2=copy.deepcopy(coef); c2['g']=(np.array(coef.g)-360*np.array(coef.aux.frq)*DT/60)%360
tt=pd.date_range('2026-10-03','2026-10-06',freq='1min'); hh=utide.reconstruct(tt,c2,verbose=False).h
shom=[("03 06:30",3.70),("03 12:00",10.11),("03 19:00",4.00),("04 00:40",9.37),("04 07:29",4.51),("04 13:14",9.27),("04 20:20",4.60),("05 02:26",8.78),("05 09:06",4.90),("05 15:10",9.08),("05 22:13",4.46)]
d=np.diff(hh); ex=[i for i in range(1,len(hh)-1) if (d[i-1]>0)!=(d[i]>0)]
loc=[(tt[i].tz_localize('UTC').tz_convert('Europe/Paris'),hh[i]) for i in ex]
dts=[]
for s,hs in shom:
    ts=pd.Timestamp(f"2026-10-{s}").tz_localize('Europe/Paris')
    tl,hl=min(loc,key=lambda x:abs(x[0]-ts)); dt=(tl-ts).total_seconds()/60; dts.append(dt)
    print(f"SHOM {s} {hs:5.2f} | nouveau {tl:%H:%M} {hl:5.2f}  ({dt:+.0f} min)")
print(f"écart moyen {np.mean(dts):+.1f} min, max {np.max(np.abs(dts)):.0f} min ; bloc écrit : {len(blob)} octets")
