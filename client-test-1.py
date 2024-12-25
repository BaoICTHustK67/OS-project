import asyncio
import websockets
import json
import tkinter as tk
from threading import Thread


class TicketClient:
    def __init__(self, root, client_name="Client 1"):
        """
        Initialize the TicketClient UI and websocket connection.
        """
        self.root = root
        self.client_name = client_name  # The name or identifier for this client
        self.root.title(f"{self.client_name} - Ticket Booking Client")
        self.ticket_status = {}  # Tracks the status of each ticket (True = booked)
        self.ticket_buttons = {}  # Holds references to ticket buttons
        self.client_bookings = {}  # Tracks which client booked which ticket
        self.websocket = None
        self.loop = asyncio.new_event_loop()
        self.running = True
        self.thread = Thread(target=self.start_event_loop, daemon=True)
        self.thread.start()

        # Create the canvas for drawing tickets
        self.canvas = tk.Canvas(root, width=600, height=500, bg="white")
        self.canvas.pack()

        self.stop_button = tk.Button(root, text="Stop", font=("Arial", 14), command=self.stop)
        self.stop_button.pack(pady=10)

        # Create and display ticket grid
        self.create_tickets()
    def create_tickets(self):
        """
        Create a grid of tickets on the canvas and bind click events.
        """
        rows, cols = 5, 5  # Adjust for the grid layout
        ticket_width, ticket_height = 80, 40
        padding = 10
        row_gap = 50  # Increase this value to add more space between the rows

        for row in range(rows):
            for col in range(cols):
                ticket_id = f"ticket_{row}_{col}"
                x1 = col * (ticket_width + padding) + padding
                y1 = row * (ticket_height + row_gap) + padding  # Apply row_gap instead of using ticket_height
                x2 = x1 + ticket_width
                y2 = y1 + ticket_height

                # Draw rectangle representing a ticket
                rect = self.canvas.create_rectangle(x1, y1, x2, y2, fill="green", tags=ticket_id)
                self.ticket_buttons[ticket_id] = rect
                self.ticket_status[ticket_id] = False  # Initially all tickets are unbooked

                # Bind click event to the rectangle
                self.canvas.tag_bind(ticket_id, "<Button-1>", lambda event, t_id=ticket_id: self.book_ticket(t_id))

                # Add space for displaying client info, with the original padding for column separation
                self.canvas.create_text(x1 + ticket_width / 2, y2 + 10, text=f"{ticket_id}", tags=f"label_{ticket_id}")

    def start_event_loop(self):
        """
        Start the asyncio event loop in a separate thread.
        """
        asyncio.set_event_loop(self.loop)
        self.loop.run_until_complete(self.connect_to_server())

    async def connect_to_server(self):
        """
        Connect to the WebSocket server and start listening for ticket updates.
        """
        uri = "ws://localhost:8765"
        try:
            async with websockets.connect(uri) as websocket:
                self.websocket = websocket
                # Listen for server messages
                while self.running:
                    message = await websocket.recv()
                    data = json.loads(message)
                    self.sync_tickets(data.get("tickets", {}))
        except Exception as e:
            print(f"WebSocket Error: {e}")

    def sync_tickets(self, ticket_data):
        """
        Synchronize ticket status with data from the server and update UI.
        """
        for ticket_id, is_booked in ticket_data.items():
            self.ticket_status[ticket_id] = is_booked
            self.update_ticket_color(ticket_id, is_booked)

    def update_ticket_color(self, ticket_id, is_booked):
        """
        Update the color of a ticket based on its booking status.
        Green = available, Red = booked.
        """
        color = "red" if is_booked else "green"
        self.canvas.itemconfig(self.ticket_buttons[ticket_id], fill=color)

        # Update client info (who booked the ticket)
        if is_booked:
            self.canvas.itemconfig(f"label_{ticket_id}", text=f"{ticket_id} - {self.client_bookings.get(ticket_id, 'N/A')}")
        else:
            self.canvas.itemconfig(f"label_{ticket_id}", text=f"{ticket_id}")

    def book_ticket(self, ticket_id):
        """
        Handle ticket booking when a rectangle is clicked.
        """
        if self.ticket_status[ticket_id]:  # If already booked
            print(f"Ticket {ticket_id} is already booked.")
            return

        # Mark the ticket as booked and send the update to the server
        self.ticket_status[ticket_id] = True
        self.client_bookings[ticket_id] = self.client_name  # Record which client booked the ticket
        self.update_ticket_color(ticket_id, True)

        # Send booking update to the server including the client name
        if self.websocket and self.websocket.open:
            asyncio.run_coroutine_threadsafe(
                self.websocket.send(json.dumps({
                    "action": "book",
                    "ticket_id": ticket_id,
                    "client_name": self.client_name  # Include client name
                })), self.loop
            )
    def stop(self):
        """
        Stop the application and the event loop.
        """
        self.running = False
        if self.loop.is_running():
            self.loop.stop()
        self.root.quit()


# Run the application
root = tk.Tk()
app = TicketClient(root, client_name="Client 1")  # You can pass different names like "Client 2" for other instances
root.mainloop()
