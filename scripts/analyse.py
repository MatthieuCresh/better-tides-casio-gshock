import numpy as np, pandas as pd, utide, copy, csv, json, warnings
warnings.filterwarnings('ignore')
LAT=48.6408
df=pd.read_csv('data/saint_malo_horaire.csv',parse_dates=['t'])
t=df.t.dt.tz_convert(None)
train=(t<'2025-01-01'); test=(t>='2025-01-01')&(t<'2026-01-01')
# 60 constituants Casio (ordre du fichier) -> noms utide
CASIO="Sa Ssa Mm MSf Mf 2Q1 SIG1 Q1 RHO1 O1 MP1 M1 CHI1 PI1 P1 S1 K1 PSI1 PHI1 THE1 J1 SO1 OO1 OQ2 MNS2 2N2 MU2 N2 NU2 OP2 M2 MKS2 LDA2 L2 T2 S2 R2 K2 MSN2 KJ2 2SM2 MO3 M3 SO3 MK3 SK3 MN4 M4 SN4 MS4 MK4 S4 SK4 2MN6 M6 MSN6 2MS6 2MK6 2SM6 MSK6".split()
UT={'Sa':'SA','Ssa':'SSA','Mm':'MM','MSf':'MSF','Mf':'MF','M1':'NO1'}
names=[UT.get(c,c.upper()) for c in CASIO]
from utide._ut_constants import ut_constants
avail=set(ut_constants.const.name)
fitnames=[n for n in names if n in avail]
missing=[c for c,n in zip(CASIO,names) if n not in avail]
print("Constituants Casio non gérés par utide (mis à 0):",missing)
coef=utide.solve(t[train],df.h[train].values,lat=LAT,constit=fitnames,method='ols',conf_int='none',nodal=True,trend=False,verbose=False)
coefall=utide.solve(t[train],df.h[train].values,lat=LAT,constit='auto',method='ols',conf_int='none',trend=False,verbose=False)
top=np.argsort(-coef.A)[:12]
print("Z0 =",round(coef.mean,3))
for i in top: print(f"  {coef.name[i]:5s} H={coef.A[i]:.3f} m  G={coef.g[i]:6.1f}°")
pickle_out={'Z0':coef.mean,'name':list(coef.name),'A':list(coef.A),'g':list(coef.g)}
json.dump(pickle_out,open('data/saint_malo_60.json','w'),indent=1)
# Casio 4 composantes
casio4={'M2':(207,3.69),'S2':(259,1.43),'K1':(112,0.10),'O1':(359,0.08),'M4':(286,0.017),'M6':(164,0.0)}
def subset(c,vals,z0,shift_h=0.0):
    c2=copy.deepcopy(c); idx=[i for i,n in enumerate(c.name) if n in vals]
    for k in ['name','A','g']: c2[k]=np.array(c[k])[idx]
    for k in ['frq','lind']: c2['aux'][k]=np.array(c['aux'][k])[idx]
    frq=c2['aux']['frq']  # cycles/h
    c2['A']=np.array([vals[n][1] for n in c2.name]); 
    c2['g']=np.array([(vals[n][0]-360*frq[j]*shift_h)%360 for j,n in enumerate(c2.name)])
    c2['mean']=z0; return c2
c46=utide.solve(t[train],df.h[train].values,lat=LAT,constit=list(casio4),method='ols',conf_int='none',trend=False,verbose=False)
print("Notre ajustement sur les mêmes 6 ondes :",{n:(round(g),round(a,3)) for n,a,g in zip(c46.name,c46.A,c46.g)})
res={}
for shift in (0,1):
    res[shift]=subset(c46,casio4,6.78,shift)
tt=pd.date_range('2025-01-01','2026-01-01',freq='5min')[:-1]
def pred(c): return utide.reconstruct(tt,c,verbose=False).h
ref=pred(coefall)
def extrema(h):
    d=np.diff(h); i=np.where((d[:-1]>0)&(d[1:]<=0))[0]+1; j=np.where((d[:-1]<0)&(d[1:]>=0))[0]+1
    return i,j
def compare(h,label):
    out={}
    for kind,(a,b) in zip(['PM','BM'],zip(extrema(ref),extrema(h))):
        dt=[];dh=[]
        for k in a:
            m=b[np.argmin(abs(b-k))]
            if abs(m-k)<36: dt.append((m-k)*5); dh.append(h[m]-ref[k])
        dt=np.array(dt);dh=np.array(dh)
        out[kind]=dict(t_moy=dt.mean(),t_abs=np.abs(dt).mean(),t_max=np.abs(dt).max(),h_abs=np.abs(dh).mean()*100,h_max=np.abs(dh).max()*100)
    print(f"\n{label}")
    for k,v in out.items(): print(f"  {k}: heure écart moyen {v['t_moy']:+.0f} min | |écart| moyen {v['t_abs']:.0f} min, max {v['t_max']:.0f} min | hauteur |écart| moyen {v['h_abs']:.0f} cm, max {v['h_max']:.0f} cm")
    return out
R={}
R['casio_utc']=compare(pred(res[0]),"Casio 4 ondes (phases lues comme UTC)")
R['casio_utc1']=compare(pred(res[1]),"Casio 4 ondes (phases lues comme UTC+1)")
R['ours60']=compare(pred(coef),"Notre jeu 60 ondes Casio (ajusté sur mesures SHOM)")
# vérif vs observations 2025 (horaire)
obs=df[test].set_index(df.t[test].dt.tz_convert(None)).h
for lab,c in [('Casio UTC+1',res[1]),('Casio UTC',res[0]),('Nos 60 ondes',coef),('Référence complète',coefall)]:
    p=utide.reconstruct(obs.index,c,verbose=False).h
    print(f"RMS vs mesures 2025 – {lab}: {np.sqrt(np.mean((p-obs.values)**2))*100:.0f} cm")
json.dump(R,open('data/resultats.json','w'),indent=1,default=float)
