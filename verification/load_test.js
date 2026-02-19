import http from 'k6/http';
import { check, sleep } from 'k6';
import ws from 'k6/ws';

// SC-002: End-to-End Latency < 30ms
export let options = {
  vus: 10,
  duration: '30s',
};

export default function () {
  const url = 'ws://localhost:4000/ws';
  const tenant = 'loadtest';
  const room = 'bench';

  // Note: Needs JWT auth generation (mocked here)
  const params = { 
    headers: { 'Authorization': 'Bearer mock_token' } 
  };

  const response = ws.connect(url, params, function (socket) {
    socket.on('open', function open() {
      // Send timestamped message
      const start = Date.now();
      socket.send(JSON.stringify({ 
        op: "publish", 
        room: room, 
        payload: "ping", 
        ts: start 
      }));
    });

    socket.on('message', function (data) {
      const msg = JSON.parse(data);
      if (msg.payload === "ping") {
        const end = Date.now();
        const latency = end - msg.ts;
        check(latency, {
          'latency < 30ms': (l) => l < 30,
        });
      }
      socket.close();
    });

    socket.on('close', () => console.log('disconnected'));
  });

  check(response, { 'status is 101': (r) => r && r.status === 101 });
  sleep(1);
}
