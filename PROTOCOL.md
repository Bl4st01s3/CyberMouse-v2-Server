# CyberMouse Communication Protocol

This document defines the network protocols used by the CyberMouse system (running on the Banana Pi) to communicate mouse, scroll, volume, and macro events to the client software running on the Main PC.

The communication is split into two channels for optimal performance:
1. **UDP Protocol (Low Latency):** Used exclusively for continuous cursor coordinate streaming.
2. **WebSocket Protocol (Reliability):** Used for discrete events like clicks, scrolls, volume changes, and system macros.

---

## 1. UDP Protocol (Cursor Coordinates)

The UDP stream sends lightweight JSON packets containing normalized cursor coordinates. The Main PC client is responsible for scaling these coordinates `[0.0 to 1.0]` to its actual screen resolution.

**Transmission Rate:** Matches the FPS of the active vision loop (up to 30-60 Hz).
**Default Port:** `9001` (Configurable)

### Payload Structure

```json
{
  "type": "cursor_move",
  "x": 0.543,
  "y": 0.210
}
```

*   `x`: Horizontal position (0.0 is left edge, 1.0 is right edge).
*   `y`: Vertical position (0.0 is top edge, 1.0 is bottom edge).

> **Note:** When the user initiates a click gesture (thumb tapping the index knuckle), the Banana Pi will implement "Cursor Locking" and continue sending the same locked X/Y coordinates to prevent the cursor from jumping right before the click registers.

---

## 2. WebSocket Protocol (Discrete Events)

The WebSocket connection handles events that must be reliably delivered without dropping.

**Default Port:** `9002` (Configurable)

### Payload Structure

All WebSocket messages are sent as JSON strings with a consistent `type` and `action` structure.

#### 2.1 Clicks
Triggered when the thumb taps the base knuckle of the index finger.
```json
{
  "type": "mouse_event",
  "action": "mouse_down"
}
```
```json
{
  "type": "mouse_event",
  "action": "mouse_up"
}
```
*(Dragging is handled by maintaining the `mouse_down` state while continuing to stream X/Y coordinates over UDP).*

#### 2.2 Scrolling
Triggered either by a pointing finger moving in a circular motion (wrist rotation) or two fingers moving linearly.
*   **Vertical Gestures:** Index pointing parallel to screen (horizontal) OR Index + Middle pointing forward moving up/down.
*   **Horizontal Gestures:** Index pointing up (vertical) OR Index + Middle pointing forward moving left/right.

```json
{
  "type": "scroll_event",
  "action": "scroll_up"
}
```
*Valid Actions:* `"scroll_up"`, `"scroll_down"`, `"scroll_left"`, `"scroll_right"`.
*(Note: Inversion logic is handled on the Banana Pi side before sending).*

#### 2.3 Volume Control
Triggered by an open hand imitating turning a large dial.

```json
{
  "type": "volume_event",
  "action": "volume_up"
}
```
*Valid Actions:* `"volume_up"`, `"volume_down"`.
*(Note: Inversion logic is handled on the Banana Pi side before sending).*

---

## Implementation Notes for Main PC Client
1. **Listen on UDP Port 9001:** Unpack JSON, read `x` and `y`, multiply by monitor width and height, and use OS-level APIs (e.g., `pyautogui` or `mouse` in Python, or Win32 API in C#) to move the cursor.
2. **Connect to WebSocket Port 9002:** Listen for incoming JSON messages and trigger the corresponding OS events.
3. **Threading:** Ensure the UDP listener and WebSocket client run on separate threads/tasks to prevent blocking.