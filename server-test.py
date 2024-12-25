# File: ticket_booking_server.py

import asyncio
import websockets
import json

# Initialize ticket data and per-ticket locks
ROWS, COLS = 5, 5
tickets = {f"ticket_{row}_{col}": False for row in range(ROWS) for col in range(COLS)}  # False = available, True = booked
ticket_locks = {ticket_id: asyncio.Lock() for ticket_id in tickets}  # Lock per ticket

# Set of connected clients
connected_clients = set()

async def notify_clients():
    """
    Notify all connected clients with the updated ticket data.
    """
    if connected_clients:  # Only send updates if there are connected clients
        message = json.dumps({"tickets": tickets})
        tasks = [asyncio.create_task(client.send(message)) for client in connected_clients]
        await asyncio.gather(*tasks)

async def handle_client(websocket, path):
    """
    Handle individual client connection.
    """
    # Add client to the set of connected clients
    connected_clients.add(websocket)
    try:
        # Send the initial ticket status to the newly connected client
        await websocket.send(json.dumps({"tickets": tickets}))

        # Handle messages from the client
        async for message in websocket:
            data = json.loads(message)
            action = data.get("action")
            ticket_id = data.get("ticket_id")

            if action == "book" and ticket_id in tickets:
                # Use the lock specific to the requested ticket
                async with ticket_locks[ticket_id]:
                    if not tickets[ticket_id]:
                        tickets[ticket_id] = True
                        print(f"Ticket {ticket_id} booked successfully.")
                        # Notify the client about success
                        await websocket.send(json.dumps({
                            "status": "success",
                            "message": f"Ticket {ticket_id} booked successfully."
                        }))
                        # Notify all clients about the update
                        await notify_clients()
                    else:
                        print(f"Ticket {ticket_id} is already booked.")
                        # Notify the client about failure
                        await websocket.send(json.dumps({
                            "status": "error",
                            "message": f"Ticket {ticket_id} is already booked."
                        }))
    except websockets.ConnectionClosed:
        print("A client disconnected.")
    finally:
        # Remove client from the set of connected clients
        connected_clients.remove(websocket)

async def main():
    """
    Start the WebSocket server.
    """
    server = await websockets.serve(handle_client, "localhost", 8765)
    print("WebSocket server is running on ws://localhost:8765")
    await server.wait_closed()

# Run the server
asyncio.run(main())
