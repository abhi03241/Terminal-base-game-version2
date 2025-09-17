# 🐍 Terminal-based Multiplayer Snake Game

A **cross-platform multiplayer Snake game** that runs entirely in the terminal using **Python**, **UDP sockets**, and **curses**.  
You can play with friends across different machines (Linux 🐧, macOS 🍎, Windows 🪟).  

---

## 🚀 Features
- Multiplayer over **UDP**
- Terminal-based interface with `curses`
- Works across **Linux, macOS, and Windows**
- Real-time gameplay with smooth controls
- Scoreboard panel with live scores
- Respawn and quit functionality

---

## 📂 Project Structure
```
.
├── client.py       # Player-side terminal client
├── server.py       # Game server handling players & game state
├── requirements.txt # Python dependencies
└── README.md       # Documentation
```

---

## ⚙️ Requirements
- Python **3.7+**
- Dependencies from `requirements.txt`

Install them with:
```bash
pip install -r requirements.txt
```

Special notes:
- **Linux/macOS** → `curses` comes pre-installed ✅
- **Windows** → you need to install:
  ```bash
  pip install windows-curses
  ```

---

## ▶️ How to Run

### 1. Start the Server (Host)
On one machine, run:
```bash
python server.py
```
By default, it listens on `0.0.0.0:9999`.  
Make sure to allow UDP traffic on port **9999** if using firewall.  

### 2. Run the Client (Players)
On the same or different machines (Linux, macOS, Windows), run:
```bash
python client.py [SERVER_IP] [SERVER_PORT] [PLAYER_NAME]
```

Example:
```bash
python client.py 192.168.1.100 9999 Abhishek
```

Defaults:
- `SERVER_IP = 127.0.0.1`
- `SERVER_PORT = 9999`
- `PLAYER_NAME = Player`

---

## 🎮 Controls
- **Arrow Keys / WASD** → Move snake
- **R** → Respawn if dead
- **Q** → Quit game

---

## 📡 Protocol (Server ↔ Client)
- Client sends:
  - `{"type":"join", "name": NAME}`
  - `{"type":"input", "id": player_id, "cmd": "<up|down|left|right|respawn>"}`
  - `{"type":"leave","id": player_id}`
- Server sends:
  - `{"type":"welcome","id":..., "grid":[w,h], "tick":...}`
  - `{"type":"state","snakes":{...},"food":(x,y)}`

---

## 🖥️ Cross-Platform Usage
- Host the **server** on **Linux, macOS, or Windows**.  
- Players can connect from any system as long as:
  - They’re on the same LAN/WiFi (use host’s local IP).
  - Or port forwarding is enabled for internet play.

Example setup:
- Server → Linux desktop at `192.168.1.50`
- Player 1 → Windows laptop:  
  ```bash
  python client.py 192.168.1.50 9999 Alice
  ```
- Player 2 → macOS:  
  ```bash
  python client.py 192.168.1.50 9999 Bob
  ```

---

## 🔮 Future Enhancements
- 🎤 In-game chat
- ⚡ Power-ups (speed boost, shield, etc.)
- 🏆 Persistent leaderboard
- 🐳 Docker support for server deployment

---

## 👨‍💻 Author
Developed by **Abhishek Shukla (Udit)** 🐍✨  

