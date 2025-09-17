#!/usr/bin/env python3
"""
client.py - curses terminal client for UDP multiplayer snake

Usage:
    python client.py [SERVER_IP] [SERVER_PORT] [NAME]

Notes:
- Server protocol expected:
  * send {"type":"join", "name": NAME}
  * send {"type":"input", "id": player_id, "cmd": "<up|down|left|right|respawn>"}
  * server sends {"type":"welcome","id":..., "grid":[w,h], "tick":...}
  * server sends {"type":"state","snakes":{...},"food":(x,y)}
- On Windows, install `windows-curses` (pip install windows-curses)
"""
import socket
import json
import threading
import curses
import time
import sys
import select

# --- config from args ---
SERVER_HOST = sys.argv[1] if len(sys.argv) >= 2 else "127.0.0.1"
SERVER_PORT = int(sys.argv[2]) if len(sys.argv) >= 3 else 9999
NAME = sys.argv[3] if len(sys.argv) >= 4 else "Player"

# --- networking ---
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.setblocking(False)

player_id = None
grid_w, grid_h = 40, 20
tick = 0.12
state = {"snakes": {}, "food": (0, 0)}
running = True

def send_join():
    msg = {"type": "join", "name": NAME}
    try:
        sock.sendto(json.dumps(msg).encode(), (SERVER_HOST, SERVER_PORT))
    except Exception:
        pass

def send_input(cmd):
    if player_id is None:
        return
    msg = {"type": "input", "id": player_id, "cmd": cmd}
    try:
        sock.sendto(json.dumps(msg).encode(), (SERVER_HOST, SERVER_PORT))
    except Exception:
        pass

def send_leave():
    if player_id is None:
        return
    try:
        sock.sendto(json.dumps({"type":"leave","id":player_id}).encode(), (SERVER_HOST, SERVER_PORT))
    except Exception:
        pass

# --- receiving thread ---
def recv_thread():
    global player_id, grid_w, grid_h, tick, state, running
    while running:
        try:
            ready = select.select([sock], [], [], 0.2)[0]
            if not ready:
                continue
            data, addr = sock.recvfrom(65536)
            try:
                msg = json.loads(data.decode())
            except Exception:
                continue
            mtype = msg.get("type")
            if mtype == "welcome":
                player_id = msg.get("id")
                grid = msg.get("grid")
                if isinstance(grid, (list, tuple)) and len(grid) >= 2:
                    grid_w, grid_h = int(grid[0]), int(grid[1])
                tick = float(msg.get("tick", tick))
            elif mtype == "state":
                # state contains 'snakes' and 'food' per server
                state = msg
            # ignore other messages
        except (BlockingIOError, InterruptedError):
            time.sleep(0.01)
        except Exception:
            # ignore socket errors and keep running
            time.sleep(0.05)

# --- drawing / UI ---
def draw_screen(stdscr):
    curses.curs_set(0)
    stdscr.nodelay(True)
    stdscr.timeout(50)

    if curses.has_colors():
        curses.start_color()
        curses.use_default_colors()
        curses.init_pair(1, curses.COLOR_GREEN, -1)   # snake body
        curses.init_pair(2, curses.COLOR_YELLOW, -1)  # snake head (you)
        curses.init_pair(3, curses.COLOR_RED, -1)     # food
        curses.init_pair(4, curses.COLOR_CYAN, -1)    # scoreboard
        curses.init_pair(5, curses.COLOR_MAGENTA, -1) # game over

    scoreboard_w = 20  # right panel width

    # request join once
    send_join()

    while True:
        stdscr.erase()
        max_y, max_x = stdscr.getmaxyx()

        # compute viewable game area (clamp to terminal size)
        # leave space for borders and scoreboard
        available_w = max_x - (scoreboard_w + 6)
        available_h = max_y - 4
        view_w = min(grid_w, max(10, available_w))
        view_h = min(grid_h, max(6, available_h))

        # Game window top-left
        game_top = 1
        game_left = 2

        # Draw border for game area using ACS chars (clamp to screen)
        gw = view_w + 2  # include left+right border
        gh = view_h + 2  # include top+bottom border
        try:
            # corners
            if game_top < max_y and game_left < max_x:
                stdscr.addch(game_top, game_left, curses.ACS_ULCORNER)
            if game_top < max_y and game_left + gw - 1 < max_x:
                stdscr.addch(game_top, game_left + gw - 1, curses.ACS_URCORNER)
            if game_top + gh - 1 < max_y and game_left < max_x:
                stdscr.addch(game_top + gh - 1, game_left, curses.ACS_LLCORNER)
            if game_top + gh - 1 < max_y and game_left + gw - 1 < max_x:
                stdscr.addch(game_top + gh - 1, game_left + gw - 1, curses.ACS_LRCORNER)
            # top/bottom
            for x in range(game_left + 1, game_left + gw - 1):
                if 0 <= game_top < max_y and 0 <= x < max_x:
                    stdscr.addch(game_top, x, curses.ACS_HLINE)
                if 0 <= game_top + gh - 1 < max_y and 0 <= x < max_x:
                    stdscr.addch(game_top + gh - 1, x, curses.ACS_HLINE)
            # sides
            for y in range(game_top + 1, game_top + gh - 1):
                if 0 <= y < max_y and 0 <= game_left < max_x:
                    stdscr.addch(y, game_left, curses.ACS_VLINE)
                if 0 <= y < max_y and 0 <= game_left + gw - 1 < max_x:
                    stdscr.addch(y, game_left + gw - 1, curses.ACS_VLINE)
        except curses.error:
            # if terminal too small, ignore drawing errors
            pass

        # offsets in-game grid to draw (we simply display top-left portion)
        view_x0 = 0
        view_y0 = 0

        # draw food (server has single tuple (x,y) or maybe list)
        food = state.get("food", None)
        if food:
            try:
                fx, fy = food
            except Exception:
                fx = fy = None
            if fx is not None:
                sx = game_left + 1 + (fx - view_x0)
                sy = game_top + 1 + (fy - view_y0)
                if 0 <= sy < max_y and 0 <= sx < max_x:
                    try:
                        if curses.has_colors():
                            stdscr.addch(sy, sx, "*", curses.color_pair(3))
                        else:
                            stdscr.addch(sy, sx, "*")
                    except curses.error:
                        pass

        # draw snakes
        snakes = state.get("snakes", {})
        for pid, pdata in snakes.items():
            segs = pdata.get("segments", [])
            alive = pdata.get("alive", True)
            name = pdata.get("name", pid)
            # choose chars/colors
            is_me = (pid == player_id)
            for i, seg in enumerate(segs):
                try:
                    x, y = seg
                except Exception:
                    continue
                sx = game_left + 1 + (x - view_x0)
                sy = game_top + 1 + (y - view_y0)
                if not (0 <= sy < max_y and 0 <= sx < max_x):
                    continue
                ch = "@" if (i == 0 and is_me) else ("O" if i == 0 else "o")
                attr = 0
                if curses.has_colors():
                    if i == 0:
                        attr = curses.color_pair(2) if is_me else curses.color_pair(1)
                    else:
                        attr = curses.color_pair(1)
                try:
                    stdscr.addch(sy, sx, ch, attr)
                except curses.error:
                    pass

        # scoreboard panel (right)
        sb_x = game_left + gw + 2
        try:
            if sb_x < max_x:
                header = " SCOREBOARD "
                if curses.has_colors():
                    stdscr.addstr(1, sb_x, header[:max_x - sb_x - 1], curses.color_pair(4) | curses.A_BOLD)
                else:
                    stdscr.addstr(1, sb_x, header[:max_x - sb_x - 1], curses.A_BOLD)
                stdscr.addstr(2, sb_x, "-" * min(len("-----------"), max_x - sb_x - 1))
                line = 3
                # build sorted scores
                score_list = []
                for pid, pdata in snakes.items():
                    score_list.append((pdata.get("score", 0), pdata.get("name", pid), pid))
                score_list.sort(reverse=True, key=lambda x: x[0])
                for sc, nm, pid in score_list[:(max_y - 10)]:
                    mark = " (YOU)" if pid == player_id else ""
                    s = f"{nm}{mark}: {sc}"
                    try:
                        stdscr.addstr(line, sb_x, s[:max_x - sb_x - 1])
                    except curses.error:
                        pass
                    line += 1
                # controls
                try:
                    stdscr.addstr(line + 1, sb_x, "Controls:")
                    stdscr.addstr(line + 2, sb_x, "Arrow keys / WASD")
                    stdscr.addstr(line + 3, sb_x, "R = Respawn")
                    stdscr.addstr(line + 4, sb_x, "Q = Quit")
                except curses.error:
                    pass
        except curses.error:
            pass

        # show your id / name at top-left area
        try:
            status = f"You: {NAME} id={player_id}"
            stdscr.addstr(0, 2, status[:max_x - 4])
        except curses.error:
            pass

        # Game Over centered message if dead
        me = snakes.get(player_id, None)
        if me is not None and not me.get("alive", True):
            msg = f" GAME OVER! Final Score: {me.get('score', 0)} "
            sub = "(Press R to Respawn or Q to Quit)"
            center_y = max_y // 2
            center_x = max_x // 2
            try:
                if curses.has_colors():
                    stdscr.addstr(center_y - 1, max(0, center_x - len(msg)//2), msg[:max_x - 1], curses.color_pair(5) | curses.A_BOLD)
                    stdscr.addstr(center_y + 1, max(0, center_x - len(sub)//2), sub[:max_x - 1], curses.color_pair(5))
                else:
                    stdscr.addstr(center_y - 1, max(0, center_x - len(msg)//2), msg[:max_x - 1], curses.A_BOLD)
                    stdscr.addstr(center_y + 1, max(0, center_x - len(sub)//2), sub[:max_x - 1])
            except curses.error:
                pass

        stdscr.refresh()

        # handle input (non-blocking)
        try:
            ch = stdscr.getch()
            if ch != -1:
                if ch in (curses.KEY_UP, ord('w'), ord('W')):
                    send_input("up")
                elif ch in (curses.KEY_DOWN, ord('s'), ord('S')):
                    send_input("down")
                elif ch in (curses.KEY_LEFT, ord('a'), ord('A')):
                    send_input("left")
                elif ch in (curses.KEY_RIGHT, ord('d'), ord('D')):
                    send_input("right")
                elif ch in (ord('r'), ord('R')):
                    send_input("respawn")
                elif ch in (ord('q'), ord('Q')):
                    send_leave()
                    break
        except Exception:
            # ignore input errors
            pass

        # small sleep to avoid busy-looping (also smooths refresh)
        time.sleep(0.01)

def main():
    global running
    t = threading.Thread(target=recv_thread, daemon=True)
    t.start()
    try:
        curses.wrapper(draw_screen)
    except KeyboardInterrupt:
        pass
    finally:
        running = False
        try:
            sock.close()
        except Exception:
            pass
        print("Client exited.")

if __name__ == "__main__":
    main()
