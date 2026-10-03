# Protocole Bluetooth LE des données de marée — Casio GBX-100 (module 3482)

Description établie par analyse de l'appli CASIO WATCHES 4.6.0 (Android) et confirmée par des captures Bluetooth entre l'appli iOS et une GBX-100, puis par des envois réussis depuis `scripts/envoi_maree.py`.

Légende : ✅ = confirmé (capture ou envoi réussi), ℹ️ = déduit, ❓ = inconnu.

## 1. Caractéristiques GATT

Service Casio `26eb000d-b012-49a8-b1f8-394fb2032b0f`. Les caractéristiques sont de la forme `26eb00XX-b012-49a8-b1f8-394fb2032b0f`.

| UUID | Rôle | Propriétés |
|---|---|---|
| `26eb002c` | Demandes de lecture `[classe, options…]` | write without response |
| `26eb002d` | Écriture de réglages `[classe, données…]` ; réponses aux lectures | write, notify |
| `26eb0023` | Contrôle des transferts « convoy » (DRSP) | write, notify |
| `26eb0024` | Données des transferts « convoy » | write without response, notify |

Les trames sur `26eb002d` sont limitées à 20 octets. Les données de marée passent par la **classe `0x2E`** : trame `[0x2E, unité, ≤ 18 octets]`.

| Unité | Contenu |
|---|---|
| 2 | Réglages de marée (6 octets) ✅ |
| 3, 4, 5 | Points « utilisateur » 1 à 3 (heure de pleine mer saisie à la main, position) ✅ |

Lecture : écrire `2E <unité>` sur `26eb002c`, puis recevoir `2E <unité> <données>` en notification sur `26eb002d`.

## 2. Réglages de marée (unité 2) ✅

| Octet | Contenu |
|---|---|
| 0 | Emplacement actif : 0 = préréglé, 1–3 = points utilisateur, **4 = APP** (données envoyées par le téléphone) |
| 1–2 | Numéro du port préréglé (uint16 LE) |
| 3–4 | Numéro du port APP (uint16 LE) |
| 5 | bit 0 : affichage en pieds |

Exemple : `04 b6 07 6b 02 00` correspond à l'emplacement APP, au port préréglé 1974 et au port APP 619 (le Saint-Malo de Casio).

- ℹ️ Si le numéro de port APP ne change pas, la montre **ne recharge pas** un nouveau bloc. Le script alterne donc 9999 et 9998.
- ℹ️ À chaque reconnexion, l'appli officielle relit l'unité 2. Si l'emplacement est APP, elle renvoie ses propres données pour ce numéro, s'il figure dans sa base.

## 3. Le bloc de marée « 60 composantes » (1009 octets) ✅

Tous les nombres sont en little-endian.

| Offset | Taille | Champ |
|---|---|---|
| 0 | 1 | Type de liste : **2** = 60 composantes |
| 1 | 18 | Nom affiché, UTF-8, complété par des zéros |
| 19 | 8 | Latitude, double, degrés (Nord positif) |
| 27 | 8 | Longitude, double, degrés, **Ouest positif** |
| 35 | 1 | Fuseau horaire en quarts d'heure (int8) : 4 = UTC+1 |
| 36 | 1 | Décalage de l'heure d'été en quarts d'heure : 4 = 1 h |
| 37 | 1 | Règle d'heure d'été : **2 = Union européenne** |
| 38 | 8 | Z0 (niveau moyen au-dessus du zéro hydrographique), double, **cm** |
| 46 | 2 | « Graph pattern » (uint16) ❓. Code alphanumérique où A–I valent 1–9 : « 2B » = 22, « 7C » = 73 |
| 48 | 480 | 60 amplitudes, doubles, **cm** |
| 528 | 480 | 60 phases, doubles, **degrés, référence UTC** (Greenwich) |
| 1008 | 1 | « HcT » ❓ (7 pour les ports français) |

**Ordre des 60 ondes** (liste japonaise standard) :
Sa, Ssa, Mm, MSf, Mf, 2Q1, σ1, Q1, ρ1, **O1**, MP1, M1, χ1, π1, **P1**, S1, **K1**, ψ1, φ1, θ1, J1, SO1, OO1, OQ2, MNS2, 2N2, μ2, **N2**, ν2, OP2, **M2**, MKS2, λ2, L2, T2, **S2**, R2, **K2**, MSN2, KJ2, 2SM2, MO3, M3, SO3, MK3, SK3, MN4, **M4**, SN4, **MS4**, MK4, S4, SK4, 2MN6, M6, MSN6, 2MS6, 2MK6, 2SM6, MSK6.

Il existe aussi un format « 4 composantes » de 163 octets (type de liste 1 : M2, S2, K1, O1 + deux ondes de petits fonds, en entiers mis à l'échelle). C'est celui que l'appli utilise pour Saint-Malo. Il n'est pas utilisé ici.

## 4. Séquence d'envoi ✅

Les connexions qui sautent la poignée de main réussissent parfois, mais la montre répond souvent « occupée ». La séquence complète ci-dessous, celle de l'appli, a toujours fonctionné.

**1. Poignée de main**, sur `26eb002c` (lecture) et `26eb002d` (écriture). « Écho » signifie relire la valeur puis la réécrire telle quelle :
- lectures `22`, `10` ;
- écriture du nom `23 "CASIO GBX-100"` (18 octets) ;
- échos `11`, `3B`, `3A` ;
- lectures `26`, `28`, `20`, `28` ;
- échos `1D`, `1E 00`, `1E 01`, `1F 00`, `1F 01`, `2F`, `45`, `2E 02` ;
- **mise à l'heure** : `09 <année u16> <mois> <jour> <h> <min> <s> <jour de semaine, dimanche = 0> <1/256 s> 01` ;
- lecture `28`.

**2. Demandes de la montre.** Elle notifie `47 01`. On répond `13`, puis `5A FF`, puis on fait deux petits transferts : catégorie `0x11` (de la montre vers le téléphone) et `3D 30`, puis catégorie `0x32` (`00 32 00 00 00 01 00`, terminé par `04 32`). On relit enfin les unités 2 à 5.

**3. Transfert du bloc.** Les notifications de `26eb0023` et `26eb0024` sont **activées au début de chaque transfert et désactivées à la fin**.
1. Écrire `00 23 F1 03 00` sur `26eb0023` (début, catégorie 0x23, longueur 1009).
2. La montre notifie sur `26eb0024` :
   - `00 00 00` si elle est prête. Sinon `00 01 <raison>` (1 pile faible, 2 température basse, 3 mémoire, **4 occupée**, 7 en préparation). Dans ce cas, envoyer `03 00` sur `26eb0024` pour abandonner, puis réessayer ;
   - puis `02 <MTU u16>`, par exemple `02 b9 00` pour une MTU de 185.
3. Envoyer le bloc en paquets `05 <MTU − 4 octets>` sur `26eb0024`, en write without response, espacés d'environ 0,4 s. Il n'y a ni CRC ni en-tête.
4. La montre notifie `04 23 …` sur `26eb0023`. On répond `04 23`.

**4. Activation.** Écrire `2E 02 <réglages>` sur `26eb002d` avec emplacement = 4 et un numéro de port APP **différent** de l'actuel.

La montre refuse aussi le transfert (« occupée ») tant qu'elle **affiche le mode marée**.

## 5. Points encore ouverts

- Sens exact de « graph pattern » et de « HcT ».
- Persistance des données lors des reconnexions automatiques de l'appli officielle.
- Format détaillé des points utilisateur (unités 3 à 5).
