"""LECTURE SEULE. Se connecte à la GBX-100 et lit les réglages de marée.
N'écrit AUCUNE donnée dans la montre (on envoie seulement des demandes de lecture 0x2E xx,
exactement comme l'appli CASIO WATCHES le fait à chaque connexion)."""
import asyncio, struct, sys, datetime
from bleak import BleakScanner, BleakClient

REQ = "26eb002c-b012-49a8-b1f8-394fb2032b0f"   # demandes de lecture
ALL = "26eb002d-b012-49a8-b1f8-394fb2032b0f"   # réponses (notifications)
LOG = open("lecture_log.txt", "a")

def log(*a):
    s = " ".join(str(x) for x in a)
    print(s); LOG.write(f"{datetime.datetime.now():%H:%M:%S} {s}\n"); LOG.flush()

async def main():
    log("=== Lecture : recherche de la montre (60 s). Appuie sur le bouton de connexion de la GBX-100 ===")
    is_casio = lambda d, adv: (d.name or adv.local_name or "").upper().startswith("CASIO")
    dev = await BleakScanner.find_device_by_filter(is_casio, timeout=60)
    if not dev:
        log("Aucune montre CASIO trouvée en 60 s.")
        return
    log(f"Trouvée : {dev.name}  adresse={dev.address}")

    replies = {}
    got = asyncio.Event()
    def on_notify(_, data: bytearray):
        log("  <- reçu :", data.hex(" "))
        if len(data) >= 2 and data[0] == 0x2E:
            replies[data[1]] = bytes(data); got.set()

    async with BleakClient(dev, timeout=20) as c:
        log("Connectée. Services Casio :")
        for s in c.services:
            if s.uuid.startswith("26eb"):
                for ch in s.characteristics:
                    log(f"   {ch.uuid}  {','.join(ch.properties)}")
        await c.start_notify(ALL, on_notify)
        for unit in (2, 3, 4, 5):
            got.clear()
            log(f"-> demande de lecture 2E {unit:02x}")
            await c.write_gatt_char(REQ, bytes([0x2E, unit]), response=False)
            try:
                await asyncio.wait_for(got.wait(), 5)
            except asyncio.TimeoutError:
                log("   (pas de réponse en 5 s)")
        await c.stop_notify(ALL)

    r = replies.get(2)
    if r:
        p = r[2:]
        slot = {0: "Preset", 1: "User1", 2: "User2", 3: "User3", 4: "APP"}.get(p[0], p[0])
        log(f"Réglages marée : emplacement={slot}  port préréglé={struct.unpack_from('<H', p, 1)[0]}"
            f"  port APP={struct.unpack_from('<H', p, 3)[0]}  pieds={bool(p[5] & 1)}")
        log("=== LECTURE RÉUSSIE ===")
    else:
        log("=== Connexion OK mais pas de réponse aux demandes de lecture ===")

try:
    asyncio.run(main())
except Exception as e:
    log("ERREUR :", type(e).__name__, e)
