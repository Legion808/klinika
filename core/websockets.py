# from fastapi import WebSocket
# from typing import Dict, List
# import logging
#
#
# class ConnectionManager:
#     def __init__(self):
#         # Map user_id to WebSocket connection
#         self.active_connections: Dict[str, WebSocket] = {}
#         self.logger = logging.getLogger("websockets")
#
#     async def connect(self, websocket: WebSocket, user_id: str):
#         """
#         Connect a new WebSocket client.
#         """
#         await websocket.accept()
#         # If user already has an active connection, close it
#         if user_id in self.active_connections:
#             try:
#                 await self.active_connections[user_id].close()
#             except Exception as e:
#                 self.logger.error(f"Error closing existing connection: {e}")
#
#         self.active_connections[user_id] = websocket
#         self.logger.info(f"User {user_id} connected. Total active connections: {len(self.active_connections)}")
#
#     def disconnect(self, user_id: str):
#         """
#         Disconnect a WebSocket client.
#         """
#         if user_id in self.active_connections:
#             del self.active_connections[user_id]
#             self.logger.info(f"User {user_id} disconnected. Total active connections: {len(self.active_connections)}")
#
#     async def send_personal_message(self, message: str, user_id: str):
#         """
#         Send a message to a specific user.
#         """
#         if user_id in self.active_connections:
#             try:
#                 await self.active_connections[user_id].send_text(message)
#             except Exception as e:
#                 self.logger.error(f"Error sending message to {user_id}: {e}")
#                 # Connection might be broken, remove it
#                 self.disconnect(user_id)
#
#     async def broadcast(self, message: str):
#         """
#         Broadcast a message to all connected clients.
#         """
#         disconnected_users = []
#         for user_id, connection in self.active_connections.items():
#             try:
#                 await connection.send_text(message)
#             except Exception as e:
#                 self.logger.error(f"Error broadcasting to {user_id}: {e}")
#                 disconnected_users.append(user_id)
#
#         # Clean up any broken connections
#         for user_id in disconnected_users:
#             self.disconnect(user_id)