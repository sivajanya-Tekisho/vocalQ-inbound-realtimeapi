import asyncio
import websockets
import json
import time

async def simulate_call():
    uri = "ws://localhost:8000/api/v1/stream"
    print(f"Connecting to {uri}...")
    try:
        async with websockets.connect(uri) as websocket:
            print("Connected!")
            
            # 1. Receive Greeting
            greeting = await websocket.recv()
            print(f"Received: {greeting}")
            
            # 2. Send Audio/Text (User says "Hello, check my order status")
            # In our mock orchestrator, we expect "transcript" event for text testing
            user_msg = {
                "event": "transcript",
                "text": "Hello, I want to check my order status."
            }
            await websocket.send(json.dumps(user_msg))
            print(f"Sent: {user_msg['text']}")
            
            # 3. Receive Response
            response = await websocket.recv()
            print(f"Received: {response}")
            
            # 4. Send another turn
            user_msg_2 = {
                "event": "transcript",
                "text": "Thanks, goodbye."
            }
            await websocket.send(json.dumps(user_msg_2))
            print(f"Sent: {user_msg_2['text']}")
            
            # 5. Receive Response
            response_2 = await websocket.recv()
            print(f"Received: {response_2}")
            
            # 6. Stop
            await websocket.send(json.dumps({"event": "stop"}))
            print("Sent Stop event")
            
            # Wait for close
            await asyncio.sleep(1)
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(simulate_call())
