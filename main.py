import asyncio
import json
import ctypes
import os
from pynput.mouse import Button, Controller as MouseController
from pynput.keyboard import Key, Controller as KeyboardController
import websockets

def get_screen_resolution():
    try:
        user32 = ctypes.windll.user32
        return user32.GetSystemMetrics(0), user32.GetSystemMetrics(1)
    except Exception as e:
        print("Warning: Could not get screen resolution via ctypes. Falling back to 1920x1080.")
        return 1920, 1080

class UDPProtocol(asyncio.DatagramProtocol):
    def __init__(self, screen_w, screen_h, mouse):
        self.screen_w = screen_w
        self.screen_h = screen_h
        self.mouse = mouse

    def connection_made(self, transport):
        self.transport = transport
        print(f"UDP Server listening for coordinates...")

    def datagram_received(self, data, addr):
        try:
            payload = json.loads(data.decode('utf-8'))
            if payload.get("type") == "cursor_move":
                x = payload.get("x")
                y = payload.get("y")
                if x is not None and y is not None:
                    # Map normalized 0.0-1.0 coords to actual screen resolution
                    abs_x = int(x * self.screen_w)
                    abs_y = int(y * self.screen_h)
                    self.mouse.position = (abs_x, abs_y)
        except Exception:
            # Silently ignore bad packets to avoid console spam
            pass

async def ws_client(pi_ip, port, mouse, keyboard):
    uri = f"ws://{pi_ip}:{port}"
    while True:
        print(f"Attempting to connect to WebSocket at {uri}...")
        try:
            async with websockets.connect(uri) as websocket:
                print(f"Successfully connected to WebSocket at {uri}")
                async for message in websocket:
                    try:
                        payload = json.loads(message)
                        msg_type = payload.get("type")
                        action = payload.get("action")

                        if msg_type == "mouse_event":
                            if action == "mouse_down":
                                mouse.press(Button.left)
                            elif action == "mouse_up":
                                mouse.release(Button.left)
                        elif msg_type == "scroll_event":
                            if action == "scroll_up":
                                mouse.scroll(0, 1)
                            elif action == "scroll_down":
                                mouse.scroll(0, -1)
                            elif action == "scroll_left":
                                mouse.scroll(-1, 0)
                            elif action == "scroll_right":
                                mouse.scroll(1, 0)
                        elif msg_type == "volume_event":
                            if action == "volume_up":
                                keyboard.press(Key.media_volume_up)
                                keyboard.release(Key.media_volume_up)
                            elif action == "volume_down":
                                keyboard.press(Key.media_volume_down)
                                keyboard.release(Key.media_volume_down)
                    except json.JSONDecodeError:
                        print("Invalid JSON received over WebSocket")
                    except Exception as e:
                        print(f"Error processing WS message: {e}")
        except Exception as e:
            print(f"WebSocket connection failed: {e}. Retrying in 5 seconds...")
            await asyncio.sleep(5)

async def main():
    # Load configuration
    if not os.path.exists("config.json"):
        print("Error: config.json not found!")
        return

    try:
        with open("config.json", "r") as f:
            config = json.load(f)
    except json.JSONDecodeError:
        print("Error: config.json is not valid JSON!")
        return

    pi_ip = config.get("pi_ip", "192.168.1.100")
    udp_port = config.get("udp_port", 9001)
    ws_port = config.get("ws_port", 9002)

    # Initialize input controllers
    mouse = MouseController()
    keyboard = KeyboardController()

    # Get screen resolution for UDP coordinate mapping
    screen_w, screen_h = get_screen_resolution()
    print(f"Detected screen resolution: {screen_w}x{screen_h}")

    loop = asyncio.get_running_loop()

    # Start UDP Server task
    print(f"Starting UDP server on 0.0.0.0:{udp_port}...")
    transport, protocol = await loop.create_datagram_endpoint(
        lambda: UDPProtocol(screen_w, screen_h, mouse),
        local_addr=('0.0.0.0', udp_port)
    )

    # Start WebSocket Client task
    ws_task = asyncio.create_task(ws_client(pi_ip, ws_port, mouse, keyboard))

    try:
        # Keep the event loop running
        await asyncio.gather(ws_task)
    except asyncio.CancelledError:
        pass
    finally:
        transport.close()

if __name__ == "__main__":
    try:
        print("Starting CyberMouse Client...")
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nCyberMouse Client stopped by user.")
