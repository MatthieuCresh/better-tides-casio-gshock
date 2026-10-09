"""Envoi d'un point de marée (bloc 60 composantes, 1009 octets) dans la GBX-100,
en rejouant la poignée de main complète de l'appli CASIO WATCHES (captures casio_larochelle / casio_granville).
Usage : python scripts/envoi_maree.py [fichier.bin] [numero_port]"""
import asyncio, struct, sys, datetime
from bleak import BleakScanner, BleakClient

REQ  = "26eb002c-b012-49a8-b1f8-394fb2032b0f"   # demandes de lecture (write without response)
ALL  = "26eb002d-b012-49a8-b1f8-394fb2032b0f"   # réponses / écritures de réglages
DRSP = "26eb0023-b012-49a8-b1f8-394fb2032b0f"   # contrôle des transferts « convoy »
CONV = "26eb0024-b012-49a8-b1f8-394fb2032b0f"   # données des transferts

BLOB_FILE = sys.argv[1] if len(sys.argv) > 1 else "data/saint_malo_3482.bin"
PORT_ID   = int(sys.argv[2]) if len(sys.argv) > 2 else 9999
RAISONS = {1: "pile faible", 2: "température basse", 3: "mémoire non effacée", 4: "occupée", 7: "en préparation"}
LOG = open("envoi_log.txt", "a")

def log(*a):
    s = " ".join(str(x) for x in a)
    print(s); LOG.write(f"{datetime.datetime.now():%H:%M:%S} {s}\n"); LOG.flush()

async def main():
    blob = open(BLOB_FILE, "rb").read()
    assert len(blob) == 1009 and blob[0] == 2, "bloc invalide"
    log(f"=== Envoi de {BLOB_FILE} ({blob[1:19].split(b'\0')[0].decode()}), port n° {PORT_ID} ===")
    log("Recherche de la montre (60 s). Mets-la sur l'écran de l'heure et appuie sur son bouton de connexion.")
    dev = await BleakScanner.find_device_by_filter(
        lambda d, adv: (d.name or adv.local_name or "").upper().startswith("CASIO"), timeout=60)
    if not dev:
        log("Aucune montre trouvée."); return
    log("Trouvée :", dev.name)

    q = {"all": asyncio.Queue(), "drsp": asyncio.Queue(), "conv": asyncio.Queue()}
    def handler(name):
        def h(_, data):
            log(f"  <- {name} :", bytes(data).hex(" ")); q[name].put_nowait(bytes(data))
        return h
    async def wait(name, pred, t=8):
        end = asyncio.get_event_loop().time() + t
        while True:
            d = await asyncio.wait_for(q[name].get(), max(0.1, end - asyncio.get_event_loop().time()))
            if pred(d): return d

    async with BleakClient(dev, timeout=20) as c:
        async def read(*cmd):
            await c.write_gatt_char(REQ, bytes(cmd), response=False)
            return await wait("all", lambda d: d[:len(cmd)] == bytes(cmd))
        async def write(data):
            await c.write_gatt_char(ALL, data, response=True)
        async def echo(*cmd):                       # relire un réglage et le renvoyer tel quel (comme l'appli)
            try:
                await write(await read(*cmd))
            except asyncio.TimeoutError:
                log(f"  (pas de réponse à {bytes(cmd).hex(' ')})")
        async def notif_on():                       # l'appli ouvre les notifications au début de chaque transfert…
            for k in ("drsp", "conv"):
                while not q[k].empty(): q[k].get_nowait()
            await c.start_notify(DRSP, handler("drsp")); await c.start_notify(CONV, handler("conv"))
        async def notif_off():                      # … et les referme à la fin
            await c.stop_notify(CONV); await c.stop_notify(DRSP)
        async def convoy_read(cat):                 # petit transfert montre -> téléphone
            await notif_on()
            await c.write_gatt_char(DRSP, bytes([0x00, cat]), response=True)
            await wait("drsp", lambda d: d[:2] == bytes([0x00, cat]))
            await asyncio.sleep(0.5)
            await c.write_gatt_char(DRSP, bytes([0x04, cat]), response=True)
            await notif_off()

        await c.start_notify(ALL, handler("all"))

        # --- 1. poignée de main de l'appli (lectures renvoyées telles quelles) ---
        log("--- Poignée de main ---")
        for cmd in (0x22, 0x10):
            try: await read(cmd)
            except asyncio.TimeoutError: log(f"  (pas de réponse à {cmd:02x})")
        name = (dev.name or "CASIO GBX-100").encode()[:18]
        await write(b"\x23" + name + bytes(18 - len(name)))
        for cmd in (0x11, 0x3b, 0x3a):
            await echo(cmd)
        for cmd in (0x26, 0x28, 0x20, 0x28):
            try: await read(cmd)
            except asyncio.TimeoutError: pass
        await echo(0x1d)
        for sub in (0, 1):
            await echo(0x1e, sub)
        for sub in (0, 1):
            await echo(0x1f, sub)
        for cmd in (0x2f, 0x45):
            await echo(cmd)
        cur = (await read(0x2e, 0x02))[2:]
        await write(b"\x2e\x02" + cur)
        log("Réglages marée actuels :", cur.hex(" "))
        # mise à l'heure (heure locale du Mac)
        n = datetime.datetime.now()
        await write(bytes([0x09]) + struct.pack("<H", n.year) + bytes([n.month, n.day, n.hour, n.minute, n.second,
                                                                       (n.weekday() + 1) % 7, int(n.microsecond / 1e6 * 256), 1]))
        log(f"Montre mise à l'heure : {n:%d/%m/%Y %H:%M:%S}")
        try: await read(0x28)
        except asyncio.TimeoutError: pass

        # --- 2. la montre signale « 47 01 » : l'appli répond 13, 5A FF, puis deux petits transferts ---
        try:
            await wait("all", lambda d: d[0] == 0x47, t=5)
        except asyncio.TimeoutError:
            log("  (pas de 47 reçu, on continue)")
        try: await read(0x13)
        except asyncio.TimeoutError: log("  (pas de réponse à 13)")
        await c.write_gatt_char(REQ, b"\x5a\xff", response=False)
        try: await wait("all", lambda d: d[0] == 0x5a)
        except asyncio.TimeoutError: pass
        try:
            await convoy_read(0x11)
        except asyncio.TimeoutError:
            log("  (transfert 0x11 sans réponse)")
        try: await read(0x3d, 0x30)
        except asyncio.TimeoutError: pass
        try:
            await notif_on()
            await c.write_gatt_char(DRSP, bytes([0x00, 0x32, 0x00, 0x00, 0x00, 0x01, 0x00]), response=True)
            await wait("drsp", lambda d: d[:2] == b"\x00\x32")
            await wait("conv", lambda d: d[0] == 0x01)
            await c.write_gatt_char(DRSP, b"\x04\x32", response=True)
            await notif_off()
        except asyncio.TimeoutError:
            log("  (transfert 0x32 sans réponse)")
        # l'appli relit encore les réglages puis attend ~20 s (choix du port par l'utilisateur)
        for unit in (2, 3, 4, 5, 2):
            try: await read(0x2e, unit)
            except asyncio.TimeoutError: pass
        log("Pause de 15 s, comme l'appli…")
        await asyncio.sleep(15)

        # --- 3. transfert du bloc marée ---
        log("--- Transfert du bloc marée ---")
        for essai in range(6):
            await notif_on()
            await c.write_gatt_char(DRSP, bytes([0x00, 0x23]) + struct.pack("<H", len(blob)) + b"\x00", response=True)
            try:
                st = await wait("conv", lambda d: d[0] == 0x00)
            except asyncio.TimeoutError:
                log("  pas de réponse au début de transfert, nouvel essai dans 10 s")
                await notif_off(); await asyncio.sleep(10); continue
            if st[1] == 0: break
            log(f"Refus : {RAISONS.get(st[2], st[2])} ({st.hex(' ')}) — fermeture propre puis nouvel essai dans 10 s")
            await c.write_gatt_char(CONV, bytes([0x03, 0x00]), response=False)   # abandon, comme l'appli
            await notif_off()
            if st[2] not in (4, 7): return
            await asyncio.sleep(10)
        else:
            log("Toujours refusé, abandon."); return
        m = await wait("conv", lambda d: d[0] in (0x02, 0x06))
        mtu = struct.unpack_from("<H", m, 1)[0]
        chunk = min(mtu - 4, c.services.get_characteristic(CONV).max_write_without_response_size - 1)
        for i in range(0, len(blob), chunk):
            await c.write_gatt_char(CONV, b"\x05" + blob[i:i+chunk], response=False)
            await asyncio.sleep(0.4)
        log(f"{len(blob)} octets envoyés en paquets de {chunk}")
        fin = await wait("drsp", lambda d: d[:2] == b"\x04\x23", t=15)
        await c.write_gatt_char(DRSP, b"\x04\x23", response=True)
        log("Transfert accepté :", fin.hex(" "))
        await notif_off()

        # --- 4. réglages : emplacement APP + numéro de port (différent de l'actuel pour forcer le rechargement) ---
        port = PORT_ID if struct.unpack_from("<H", cur, 3)[0] != PORT_ID else PORT_ID ^ 1
        new = bytearray(cur); new[0] = 4; struct.pack_into("<H", new, 3, port)
        await write(b"\x2e\x02" + bytes(new))
        chk = (await read(0x2e, 0x02))[2:]
        log(f"Réglages écrits (port {port}) : {bytes(new).hex(' ')} -> relecture {'OK' if chk == bytes(new) else chk.hex(' ')}")
        await c.stop_notify(ALL)
    log("=== TERMINÉ ===")

try:
    asyncio.run(main())
except Exception as e:
    log("ERREUR :", type(e).__name__, e)
