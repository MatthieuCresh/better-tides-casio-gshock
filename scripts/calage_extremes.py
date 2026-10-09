"""Recale des constantes harmoniques sur des heures et hauteurs de pleines/basses mers officielles
(annuaire, table de marée : SHOM, NOAA, UKHO, CHS...), avec validation sur une période mise de côté.

Principe : à l'heure exacte d'une PM ou BM officielle, la courbe prédite doit être « à plat » (dérivée nulle)
et à la hauteur officielle. La courbe étant une somme d'ondes, ces deux conditions sont linéaires en
a_j = A_j cos g_j et b_j = A_j sin g_j : on résout un problème de moindres carrés. Une pénalité (lambda)
retient la solution près des constantes de départ pour ne pas « sur-apprendre » les points de calage.

Entrées :
  constantes.json : constantes de départ (sortie de analyse.py)
  extremes.csv    : colonnes t (date et heure), type (HW ou LW), h (hauteur en m, même zéro que les constantes)
Usage :
  python scripts/calage_extremes.py constantes.json extremes.csv sortie.json LATITUDE FUSEAU FIN_CALAGE
  ex. : ... data/saint_malo_60.json annuaire.csv data/saint_malo_cale.json 48.64 Europe/Paris 2026-08-01
  FUSEAU : fuseau des heures du fichier (« UTC » si elles sont déjà en UTC)
  FIN_CALAGE : les marées avant cette date servent au calage, celles après à la validation"""
import sys, json, copy, warnings
import numpy as np, pandas as pd, utide
warnings.filterwarnings('ignore')

SRC, EXT, OUT = sys.argv[1], sys.argv[2], sys.argv[3]
LAT = float(sys.argv[4]); TZ = sys.argv[5]; SPLIT = pd.Timestamp(sys.argv[6])
LAMBDAS = [0.3, 1, 3, 10, 30]          # forces de rappel testées ; la meilleure est choisie sur la validation

# --- constantes de départ, dans une structure utide (corrections nodales comprises) ---
d = json.load(open(SRC))
tt = pd.date_range('2020-01-01', periods=24 * 400, freq='h')
coef = utide.solve(tt, np.random.default_rng(0).normal(size=len(tt)), lat=LAT, constit=d['name'],
                   method='ols', conf_int='none', trend=False, verbose=False)
coef['A'] = np.array([dict(zip(d['name'], d['A']))[n] for n in coef.name])
coef['g'] = np.array([dict(zip(d['name'], d['g']))[n] for n in coef.name])
coef['mean'] = d['Z0']
N = len(coef.name)

def basis(times):
    """Matrice (len(times), 2N+1) : h(t) = B @ x avec x = [a_1..a_N, b_1..b_N, Z0]."""
    B = np.zeros((len(times), 2 * N + 1)); B[:, -1] = 1
    for j in range(N):
        for k, g in ((j, 0.0), (N + j, 90.0)):
            c = copy.deepcopy(coef)
            for key in ('name',): c[key] = np.array([coef.name[j]])
            c['A'] = np.array([1.0]); c['g'] = np.array([g]); c['mean'] = 0.0
            for key in ('frq', 'lind'): c['aux'][key] = np.array([coef['aux'][key][j]])
            B[:, k] = utide.reconstruct(times, c, verbose=False).h
    return B

def x_of(c):
    g = np.radians(c['g']); return np.concatenate([c['A'] * np.cos(g), c['A'] * np.sin(g), [c['mean']]])

def coef_of(x):
    c = copy.deepcopy(coef); a, b = x[:N], x[N:2 * N]
    c['A'] = np.hypot(a, b); c['g'] = np.degrees(np.arctan2(b, a)) % 360; c['mean'] = x[-1]; return c

# --- extrêmes officiels, convertis en UTC ---
ex = pd.read_csv(EXT)
t = pd.to_datetime(ex.t)
t = t.dt.tz_localize(TZ, ambiguous='NaT', nonexistent='NaT') if TZ != 'UTC' else t.dt.tz_localize('UTC')
ex['tu'] = t.dt.tz_convert('UTC').dt.tz_localize(None); ex = ex.dropna(subset=['tu']).reset_index(drop=True)
train, valid = ex[ex.tu < SPLIT].reset_index(drop=True), ex[ex.tu >= SPLIT].reset_index(drop=True)
print(f"{len(train)} PM/BM pour le calage, {len(valid)} pour la validation")

# --- équations : dérivée nulle (convertie en minutes) et hauteur juste (en cm) à chaque extrême ---
dt = pd.Timedelta(seconds=60)   # pas des différences finies : D1 en m/min, D2 en m/min²
Bm, B0, Bp = basis(train.tu - dt), basis(train.tu), basis(train.tu + dt)
x0 = x_of(coef)
D1 = (Bp - Bm) / 2              # dérivée (m/min)
D2 = Bp - 2 * B0 + Bm           # dérivée seconde (m/min²), pour convertir une pente en minutes
curv = np.abs(D2 @ x0); curv[curv < 1e-5] = 1e-5
rows_t = D1 / curv[:, None]                        # ≈ erreur d'heure en minutes
rows_h = B0 * 100; rhs_h = train.h.values * 100    # erreur de hauteur en cm

def fit(lam):
    A = np.vstack([rows_t, rows_h, lam * 100 * np.eye(len(x0))])       # rappel exprimé en cm
    b = np.concatenate([np.zeros(len(rows_t)), rhs_h, lam * 100 * x0])
    return np.linalg.lstsq(A, b, rcond=None)[0]

def evaluate(c, events):
    """Heures/hauteurs prédites des PM/BM au voisinage de chaque extrême officiel (pas de 1 min)."""
    res = []
    for _, e in events.iterrows():
        w = pd.date_range(e.tu - pd.Timedelta(minutes=120), e.tu + pd.Timedelta(minutes=120), freq='1min')
        h = utide.reconstruct(w, c, verbose=False).h
        i = int(np.argmax(h) if e.type == 'HW' else np.argmin(h))
        if 0 < i < len(w) - 1:
            res.append(((w[i] - e.tu).total_seconds() / 60, (h[i] - e.h) * 100, e.h))
    return pd.DataFrame(res, columns=['dt_min', 'dh_cm', 'h'])

def summary(r, label):
    # vives-eaux : le tiers des PM les plus hautes et des BM les plus basses ; mortes-eaux : l'inverse
    pm = r.h > r.h.median()
    spring = (pm & (r.h > r[pm].h.quantile(.67))) | (~pm & (r.h < r[~pm].h.quantile(.33)))
    neap = (pm & (r.h < r[pm].h.quantile(.33))) | (~pm & (r.h > r[~pm].h.quantile(.67)))
    print(f"{label:24s} heure |moy| {r.dt_min.abs().mean():4.1f} min (max {r.dt_min.abs().max():3.0f}) | "
          f"biais vives-eaux {r[spring].dt_min.mean():+5.1f} min, mortes-eaux {r[neap].dt_min.mean():+5.1f} min | "
          f"hauteur |moy| {r.dh_cm.abs().mean():4.1f} cm")
    return r.dt_min.abs().mean()

print("\nValidation (marées non utilisées pour le calage) :")
base = summary(evaluate(coef, valid), 'Constantes de départ')
best = None
for lam in LAMBDAS:
    c = coef_of(fit(lam)); score = summary(evaluate(c, valid), f'Calé, lambda = {lam}')
    if best is None or score < best[0]: best = (score, lam, c)
score, lam, c = best
print(f"\nRetenu : lambda = {lam}. Recalage final sur toutes les marées disponibles.")
# recalage final avec toutes les données, même lambda
train = ex; Bm, B0, Bp = basis(ex.tu - dt), basis(ex.tu), basis(ex.tu + dt)
D1, D2 = (Bp - Bm) / 2, Bp - 2 * B0 + Bm
curv = np.abs(D2 @ x0); curv[curv < 1e-5] = 1e-5
rows_t, rows_h, rhs_h = D1 / curv[:, None], B0 * 100, ex.h.values * 100
c = coef_of(fit(lam))
json.dump({'Z0': float(c['mean']), 'name': list(c.name), 'A': [float(v) for v in c.A], 'g': [float(v) for v in c.g]},
          open(OUT, 'w'), indent=1)
print('Constantes recalées écrites dans', OUT)
