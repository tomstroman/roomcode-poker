# roomcode-poker
Play poker in person with digital cards and chips!

A lightweight backend server for running browser-based multiplayer poker games with real-time updates and simple setup via room codes.

(Is this README unusually rich in emoji content? Yes, it is. That's because this is
*also* an attempt to get a feel for ChatGPT as a programming companion.)

## 🎯 Project Goals

`roomcode-poker` aims to replicate the feel of in-person poker games with digital cards and chips:
- No account system or long-term persistence
- Easy game creation via room codes (similar to Jackbox-style games)
- Smooth reconnection and in-room player verification
- Fast and lightweight enough to run on a small cloud VM

## 🛠 Tech Stack

- **Backend Framework**: Python + FastAPI
- **Real-time Communication**: WebSockets (ASGI-compatible)
- **Frontend Compatibility**: Works with static HTML or a dynamic frontend like React
- **Hosting Target**: Ubuntu Linux on EC2, VPS, or Docker

## 🚀 Getting Started

### Requirements

- Python 3.10+
- Node.js (optional, if building a frontend)
- `uvicorn` and `fastapi` Python packages

### Setup Instructions (Ubuntu)

1. **Clone the repo**

```bash
git clone https://github.com/tomstroman/roomcode-poker.git
cd roomcode-poker
```

2. **Create a virtual environment and install dependencies**

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

3. **Run the development server**

To start the FastAPI development server with support for both REST and WebSocket endpoints:

```bash
uvicorn app.main:fastapi_app --host 0.0.0.0 --port 8193 --reload
```

By default, this will serve:
- REST endpoints like `POST /create-game/` for game creation
- WebSocket connections at `/ws/{room_code}/{player_id}/`
- A minimal browser-based test interface at `/ws-test/` for connecting to a room and sending messages

To try the test interface, start the server, open your browser, and visit:

```
http://localhost:8193/ws-test/
```

Use the form to:
- Create a game (room code)
- Enter a room code and player ID
- Connect to the game via WebSocket
- Send and receive broadcast messages
- Disconnect cleanly

You can open the test page in multiple browser tabs to simulate multiple players.


### Environment Variables (Optional)

Create a `.env` file to override defaults:

```env
PORT=8193
ENV=development
```

## 🧪 Feature Highlights

- 🃏 Card shuffling and dealing logic
- 💬 Real-time updates via WebSockets
- 👥 Player tracking per room
- 🔄 Reconnection handling
- ✅ Player rejoin verification mechanism (e.g. voting)

## 🔐 Deployment Notes

- Run behind Nginx as a reverse proxy
- Use TLS (e.g. Let's Encrypt)
- Consider Docker for isolated deployment
- Use `gunicorn` with `uvicorn.workers.UvicornWorker` for production

## 📝 License

This project is licensed under the MIT License. See `LICENSE` for details.

---

MIT © 2025 [Thomas Stroman]
