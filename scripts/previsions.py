import json,numpy as np,pandas as pd,utide,warnings,sys
warnings.filterwarnings('ignore')
df=pd.read_csv('data/saint_malo_horaire.csv',parse_dates=['t']); t=df.t.dt.tz_convert(None)
names=json.load(open('data/saint_malo_60.json'))['name']
coef=utide.solve(t,df.h.values,lat=48.6408,constit=names,method='ols',conf_int='none',trend=False,verbose=False)
start=pd.Timestamp(sys.argv[1] if len(sys.argv)>1 else pd.Timestamp.utcnow().strftime('%Y-%m-%d'))
tt=pd.date_range(start,periods=3*24*60,freq='1min')
h=utide.reconstruct(tt,coef,verbose=False).h
d=np.diff(h)
for i in range(1,len(h)-1):
    if (d[i-1]>0)!=(d[i]>0):
        loc=(tt[i].tz_localize('UTC').tz_convert('Europe/Paris'))
        print(f"{'PM' if d[i-1]>0 else 'BM'}  {loc:%a %d/%m %H:%M}  {h[i]:5.2f} m")
