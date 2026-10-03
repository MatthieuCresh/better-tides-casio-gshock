import struct, sys, collections
data=open(sys.argv[1],'rb').read()
recs=[];o=0
while o+13<=len(data):
    L,=struct.unpack_from('<I',data,o); secs,us=struct.unpack_from('<II',data,o+4); typ=data[o+12]; body=data[o+13:o+4+L]
    recs.append((secs+us/1e6,typ,body)); o+=4+L
types=collections.Counter(t for _,t,_ in recs); print("records",len(recs),dict(types))
t0=recs[0][0]
buf={}; att=[]
for ts,typ,b in recs:
    if typ==0xfc: continue
    if typ in (2,3) and len(b)>=4:
        h,l=struct.unpack_from('<HH',b,0); handle=h&0xfff; pb=(h>>12)&3; p=b[4:4+l]
        key=(handle,typ)
        if pb in (0,2): buf[key]=bytearray(p)
        else: buf.setdefault(key,bytearray()).extend(p)
        x=buf[key]
        if len(x)>=4:
            ln,cid=struct.unpack_from('<HH',x,0)
            if len(x)>=4+ln:
                pl=bytes(x[4:4+ln]); buf[key]=bytearray()
                if cid==4: att.append((ts-t0,'TX' if typ==2 else 'RX',handle,pl))
names={0x01:'ERR',0x02:'MTUreq',0x03:'MTUrsp',0x08:'RdByType',0x09:'RdByTypeRsp',0x0a:'Read',0x0b:'ReadRsp',0x10:'RdGrp',0x11:'RdGrpRsp',0x12:'WriteReq',0x13:'WriteRsp',0x52:'WriteCmd',0x1b:'Notif',0x1d:'Ind',0x1e:'Conf',0x04:'FindInfo',0x05:'FindInfoRsp'}
for ts,d,h,p in att:
    op=p[0]; n=names.get(op,hex(op))
    if op in (0x12,0x52,0x1b,0x1d,0x0a):
        ah=struct.unpack_from('<H',p,1)[0]; print(f"{ts:8.3f} {d} {n:9s} h=0x{ah:04x} len={len(p)-3:4d} {p[3:].hex(' ')[:120]}")
    else:
        print(f"{ts:8.3f} {d} {n:9s} {p[1:].hex(' ')[:120]}")
