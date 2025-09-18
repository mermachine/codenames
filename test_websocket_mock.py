#!/usr/bin/env python
"""Test WebSocket connection to mock server"""

import asyncio
import websockets
import json

async def test_connection():
    """Connect and receive game updates"""
    uri = "ws://localhost:8765"

    try:
        async with websockets.connect(uri) as websocket:
            print("Connected to mock server!")

            # Receive messages for 30 seconds
            timeout = 30
            start = asyncio.get_event_loop().time()

            while asyncio.get_event_loop().time() - start < timeout:
                try:
                    message = await asyncio.wait_for(websocket.recv(), timeout=1.0)
                    data = json.loads(message)

                    # Print chat messages to check for identity confusion
                    if "shared_context" in data:
                        for msg in data["shared_context"][-3:]:  # Last 3 messages
                            if not msg.get("isPrivate"):
                                print(f"[{msg['team']}] {msg['speaker']}: {msg['message'][:100]}")

                    if "phase" in data:
                        print(f"\n=== Phase: {data['phase']} ===")

                except asyncio.TimeoutError:
                    continue
                except Exception as e:
                    print(f"Error processing message: {e}")

    except Exception as e:
        print(f"Connection error: {e}")

if __name__ == "__main__":
    print("Testing WebSocket mock server...")
    asyncio.run(test_connection())