# Marées SHOM dans une G-Shock GBX-100

Envoyer à une **Casio G-Shock GBX-100** (module 3482) des constantes de marée calculées à partir des **mesures du SHOM**, à la place des données approximatives fournies par l'appli CASIO WATCHES. La montre affiche ensuite les marées de Saint-Malo à la minute près, **hors connexion**, avec son écran d'origine (graphe, PM/BM, lune, soleil).

<p align="center">
  <img src="docs/img/montre_maree.jpg" width="340" alt="GBX-100 en mode marée affichant ST-MALO SHOM : pleine mer 0:39 943 cm, basse mer 19:01 398 cm">
  <img src="docs/img/montre_heure.jpg" width="340" alt="GBX-100 sur l'écran principal avec le graphe de marée ST-MALO SHOM">
</p>

<p align="center"><em>La montre le 3 octobre 2026 après l'envoi. Elle affiche une basse mer à 19:01 (398 cm) et une pleine mer à 0:39 (943 cm). L'annuaire SHOM donne 19:00 (4,00 m) et 00:40 (9,37 m). La version calée sur les mesures du marégraphe, au lieu de l'annuaire, donnait 19:13.</em></p>

> *English summary: tools to compute 60-constituent harmonic tide constants from French SHOM tide-gauge data and upload them to a Casio G-Shock GBX-100 over Bluetooth LE, replacing Casio's coarse 4-constituent port data. Includes a description of the watch's tide-data BLE protocol.*

| | Écart moyen sur l'heure des PM/BM | Écart max |
|---|---|---|
| Données Casio d'origine (Saint-Malo, 4 ondes) | ~30 min | 1 h 40 |
| Nos constantes (60 ondes, mesures SHOM) | ~3 min | 15 min |
| Version alignée sur l'annuaire SHOM, test sur la montre | ≤ 1 min | — |

*Écarts mesurés sur 2025, par rapport à une prédiction complète, et vérifiés sur la montre (3 octobre 2026 : BM 19:01 et PM 0:39, contre 19:00 et 00:40 dans l'annuaire SHOM).*

## Pourquoi

Pour Saint-Malo, l'appli Casio n'envoie que **4 ondes harmoniques** (M2, S2, K1, O1, plus deux petites ondes de petits fonds). Il manque notamment N2 (0,71 m), K2 (0,41 m), M4 et MS4, ce qui est énorme pour l'un des plus grands marnages d'Europe. Or le firmware de la montre **sait calculer une marée à 60 ondes** : l'appli s'en sert pour d'autres ports (Japon, États-Unis, une partie de la France). Il suffit de lui fournir un jeu de 60 constantes correct.

## Comment ça marche

1. **Mesures :** hauteurs d'eau horaires du marégraphe SHOM de Saint-Malo (réseau REFMAR, 2019-2025).
2. **Analyse harmonique** avec [`utide`](https://github.com/wesleybowman/UTide), restreinte aux 60 ondes que la montre sait calculer.
3. **Conversion** au format binaire attendu par la montre : un bloc de 1009 octets (voir [docs/PROTOCOLE.md](docs/PROTOCOLE.md)).
4. **Envoi Bluetooth** depuis un Mac (ou un PC) avec [`bleak`](https://github.com/hbldh/bleak). Le script rejoue la séquence de l'appli officielle.

Option : un décalage de 12 minutes aligne les heures sur l'**annuaire officiel du SHOM**, qui est en avance de quelques minutes sur les mesures du marégraphe (voir plus bas).

## Utilisation

Prérequis : Python 3.10 ou plus et un ordinateur avec Bluetooth LE. Testé sur macOS 26 (Apple Silicon).

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```

Toutes les commandes se lancent depuis la racine du dépôt.

### Envoyer les marées de Saint-Malo (constantes déjà fournies)

1. Coupez le Bluetooth du téléphone appairé à la montre, sinon il prendra la connexion.
2. Mettez la montre sur l'**écran de l'heure**. En mode marée, elle refuse le transfert.
3. Lancez la commande, puis appuyez sur le bouton de connexion de la montre :

```bash
python scripts/envoi_maree.py data/saint_malo_3482_shom.bin
```

La montre doit ensuite afficher « ST-MALO SHOM » en mode marée. Utilisez `data/saint_malo_3482.bin` pour la version calée sur les mesures plutôt que sur l'annuaire.

Pour lire seulement les réglages de marée, sans rien écrire :

```bash
python scripts/lecture_montre.py
```

### Recalculer les constantes, ou les calculer pour un autre port

```bash
python scripts/telecharger_refmar.py 410 2019 2025 data/saint_malo_horaire.csv
python scripts/analyse.py
python scripts/constantes_casio.py
python scripts/gen_blob.py
python scripts/aligne_shom.py
python scripts/previsions.py 2026-10-03
```

Les étapes :
- `telecharger_refmar.py` télécharge les mesures (410 = Saint-Malo ; la liste des marégraphes est sur [data.shom.fr](https://data.shom.fr)).
- `analyse.py` fait l'analyse harmonique et la compare au modèle Casio. Il produit `data/saint_malo_60.json`.
- `constantes_casio.py` produit les constantes au format Casio.
- `gen_blob.py` produit le bloc de 1009 octets.
- `aligne_shom.py` est optionnel : il applique le décalage vers l'annuaire et vérifie le résultat.
- `previsions.py` affiche les PM/BM prévues pour comparer avec la montre.

Bonus : `parse_pklg.py` décode une capture Bluetooth PacketLogger (macOS/iOS) en liste d'opérations GATT.

Pour un autre port, il faut adapter l'identifiant du marégraphe, les coordonnées, le nom affiché (18 caractères au maximum), ainsi que les marées de l'annuaire utilisées dans `aligne_shom.py`. `analyse.py` contient aussi les constantes Casio de Saint-Malo, qui ne servent qu'à la comparaison.

## Mesures ou annuaire ?

Sur 2025, données qui n'ont pas servi à l'ajustement, notre modèle colle aux mesures : erreur quadratique minimale à 0 minute de décalage, PM +5 min et BM +1 min en moyenne. L'annuaire SHOM est environ 12 minutes plus tôt que notre modèle. Le 3 octobre 2026, le marégraphe a mesuré BM 06:37 et PM 12:06, quand l'annuaire donnait 06:30 et 12:00 et notre modèle 06:42 et 12:08 : la réalité se situe entre les deux. `aligne_shom.py` permet de choisir l'annuaire comme référence.

## Limites et précautions

- **Projet personnel, non affilié à Casio ni au SHOM.** À utiliser à vos risques. Le pire cas rencontré est réversible : resélectionner un port dans l'appli CASIO WATCHES remet les données d'origine.
- **L'appli Casio peut écraser les données.** À chaque reconnexion, elle renvoie ses propres données pour le numéro de port enregistré. Le script utilise un numéro inconnu de l'appli (9999 ou 9998) pour l'éviter. La persistance sur plusieurs jours reste à confirmer.
- Le script **met la montre à l'heure** de l'ordinateur, comme le fait l'appli.
- Ce n'est **pas un instrument de navigation**. Les prédictions n'incluent pas les effets météo (surcotes de 10 à 20 cm courantes). Référez-vous aux documents officiels du SHOM.
- Testé uniquement sur une GBX-100, avec Saint-Malo.

## Sources, licences et crédits

- **Mesures marégraphiques :** © SHOM, réseau REFMAR, [data.shom.fr](https://data.shom.fr), [Licence Ouverte Etalab 2.0](https://www.etalab.gouv.fr/licence-ouverte-open-licence/). Elles ne sont pas incluses : `telecharger_refmar.py` les récupère. Les constantes fournies dans `data/` en sont dérivées.
- **Protocole :** déterminé par analyse de l'appli CASIO WATCHES 4.6.0, à seule fin d'interopérabilité (directive 2009/24/CE, art. 6), et confirmé par des captures Bluetooth. Ce dépôt ne contient ni code ni fichiers de Casio ; seules les 6 constantes Casio de Saint-Malo sont citées dans `analyse.py` pour la comparaison. Le travail de reverse-engineering de [Gadgetbridge](https://gadgetbridge.org) sur les montres Casio a servi de point de départ.
- **Code :** licence MIT (voir [LICENSE](LICENSE)).
