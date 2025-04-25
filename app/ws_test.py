ws_test_html = (
    """
    <!DOCTYPE html>
    <html lang="en">
    <head>
      <meta charset="UTF-8">
      <title>Poker WebSocket Test</title>
      <style>
        #log { white-space: pre-wrap; }
      </style>
    </head>
    <body>
      <h1>Poker WebSocket Test</h1>

      <div>
        <label>Stack Size: <input type="number" id="stackSize" value="5000"></label>
        <button onclick="createGame()">Create Game</button>
      </div>

      <div style="margin-top: 1em;">
        <label>Room Code: <input type="text" id="roomCode"></label>
        <label>Player ID: <input type="text" id="playerId" value="player123"></label>
        <button id="connectBtn" onclick="connectWebSocket()">Connect</button>
        <button id="disconnectBtn" style="display: none;" """
    """onclick="disconnectWebSocket()">Disconnect</button>
      </div>

      <div style="margin-top: 1em;">
        <label>Message: <input type="text" id="message"></label>
        <button onclick="sendMessage()">Send</button>
      </div>

      <pre id="log" style="margin-top: 2em; background: #eee; padding: 1em;"></pre>

      <script>
        let ws;

        function log(message) {
          document.getElementById("log").textContent += message + "\\n";
        }

        async function createGame() {
          const stackSize = document.getElementById("stackSize").value;
          const res = await fetch("http://localhost:8193/create-game/", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ stack_size: Number(stackSize) })
          });

          const data = await res.json();
          document.getElementById("roomCode").value = data.code;
          log(`Game created with code: ${data.code}`);
        }

        function connectWebSocket() {
          const roomCode = document.getElementById("roomCode").value;
          const playerId = document.getElementById("playerId").value;
          const url = `ws://localhost:8193/ws/${roomCode}/${playerId}/`;

          ws = new WebSocket(url);
          ws.onopen = () => {
            log("WebSocket connected.");
            document.title = `Player: ${playerId}`;
            toggleConnectionButtons(true);
          };
          ws.onmessage = (event) => {
            log(`Received: ${event.data}`);
          };
          ws.onclose = () => {
            log("WebSocket disconnected.");
            document.title = "Poker WebSocket Test";
            toggleConnectionButtons(false);
          };
        }

        function disconnectWebSocket() {
          if (ws && ws.readyState === WebSocket.OPEN) {
            ws.close(1000, "User disconnected");
          }
        }

        function sendMessage() {
          const msg = document.getElementById("message").value;
          if (ws && ws.readyState === WebSocket.OPEN) {
            const playerId = document.getElementById("playerId").value;
            const jsonMsg = { playerId, msg };
            ws.send(JSON.stringify(jsonMsg));
            log(`Sent: ${JSON.stringify(jsonMsg)}`);
          } else {
            log("WebSocket is not connected.");
          }
        }
        function toggleConnectionButtons(connected) {
          document.getElementById("connectBtn").style.display = """
    """connected ? "none" : "inline-block";
          document.getElementById("disconnectBtn").style.display = """
    """connected ? "inline-block" : "none";
        }

      </script>
    </body>
    </html>
    """
)
