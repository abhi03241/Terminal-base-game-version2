#!/usr/bin/env python3
"""
server.py - UDP multiplayer snake server
"""

import socket, json, threading, time, random

SERVER_HOST = "0.0.0.0"
SERVER_PORT = 9999

grid_w, grid_h = 40, 20
tick = 0.12

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.bind((SERVER_HOST, SERVER_PORT))

clients = {}  # id -> (addr, name)
snakes = {}   # id -> snake data
next_id = 1
food = (random.randint(1, grid_w-2), random.randint(1, grid_h-2))

lock = threading.Lock()

def make_food():
    while True:
        fx = random.randint(1, grid_w-2)
        fy = random.randint(1, grid_h-2)
        ok = True
        for s in snakes.values():
            if (fx, fy) in s["segments"]:
                ok = False
                break
        if ok:
            return (fx, fy)

def handle_message(data, addr):
    global next_id, food
    try:
        msg = json.loads(data.decode())
    except:
        return
    t = msg.get("type")
    if t == "join":
        name = msg.get("name","?")
        with lock:
            global next_id
            pid = str(next_id)
            next_id += 1
            clients[pid] = (addr, name)
            # spawn snake
            x = random.randint(5, grid_w-6)
            y = random.randint(5, grid_h-6)
            snakes[pid] = {
                "id": pid,
                "name": name,
                "segments": [(x,y),(x-1,y),(x-2,y)],
                "dir": "right",
                "alive": True,
                "score": 0
            }
            welcome = {"type":"welcome","id":pid,"grid":[grid_w,grid_h],"tick":tick}
            sock.sendto(json.dumps(welcome).encode(), addr)
    elif t == "input":
        pid = msg.get("id")
        cmd = msg.get("cmd")
        if pid in snakes:
            s = snakes[pid]
            if cmd=="respawn":
                if not s["alive"]:
                    x = random.randint(5, grid_w-6)
                    y = random.randint(5, grid_h-6)
                    s["segments"] = [(x,y),(x-1,y),(x-2,y)]
                    s["dir"] = "right"
                    s["alive"] = True
                    s["score"] = 0
            elif s["alive"]:
                d = s["dir"]
                if cmd=="up" and d!="down": s["dir"]="up"
                elif cmd=="down" and d!="up": s["dir"]="down"
                elif cmd=="left" and d!="right": s["dir"]="left"
                elif cmd=="right" and d!="left": s["dir"]="right"
    elif t == "leave":
        pid = msg.get("id")
        with lock:
            snakes.pop(pid, None)
            clients.pop(pid, None)

def recv_loop():
    while True:
        data, addr = sock.recvfrom(65536)
        handle_message(data, addr)

def game_loop():
    global food
    while True:
        time.sleep(tick)
        with lock:
            for pid,s in list(snakes.items()):
                if not s["alive"]:
                    continue
                head = s["segments"][0]
                dx,dy = 0,0
                if s["dir"]=="up": dy=-1
                elif s["dir"]=="down": dy=1
                elif s["dir"]=="left": dx=-1
                elif s["dir"]=="right": dx=1
                new_head = (head[0]+dx, head[1]+dy)

                # border collision
                if new_head[0] <= 0 or new_head[0] >= grid_w-1 or new_head[1] <= 0 or new_head[1] >= grid_h-1:
                    s["alive"] = False
                    continue

                # self collision
                if new_head in s["segments"]:
                    s["alive"] = False
                    continue

                # other snake collision
                for oid, os in snakes.items():
                    if oid==pid: continue
                    if new_head in os["segments"]:
                        s["alive"] = False
                        break
                if not s["alive"]:
                    continue

                # move
                s["segments"].insert(0, new_head)
                if new_head == food:
                    s["score"] += 1
                    food = make_food()
                else:
                    s["segments"].pop()

            # broadcast
            state = {"type":"state","snakes":snakes,"food":food}
            encoded = json.dumps(state).encode()
            for pid,(addr,name) in clients.items():
                try: sock.sendto(encoded, addr)
                except: pass

def main():
    print(f"[SERVER] Listening on {SERVER_HOST}:{SERVER_PORT}")
    threading.Thread(target=recv_loop,daemon=True).start()
    game_loop()

if __name__=="__main__":
    main()

