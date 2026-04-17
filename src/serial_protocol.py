"""
CA-410 Serial Protocol Layer
Encapsulates pyserial communication with CR (\r) delimiter handling.
All serial I/O must happen in the worker thread, never in the main GUI thread.
"""

import serial
import serial.tools.list_ports
from typing import Optional


class CA410Protocol:
    """Low-level serial communication wrapper for CA-410 colorimeter."""

    BAUDRATE = 9600
    TIMEOUT = 3.0  # seconds

    def __init__(self, port: str):
        self.port = port
        self.serial: Optional[serial.Serial] = None

    def open(self) -> None:
        """Open the serial port."""
        self.serial = serial.Serial(
            port=self.port,
            baudrate=self.BAUDRATE,
            bytesize=serial.EIGHTBITS,
            stopbits=serial.STOPBITS_ONE,
            parity=serial.PARITY_NONE,
            timeout=self.TIMEOUT,
        )
        self.serial.flushInput()

    def close(self) -> None:
        """Close the serial port."""
        if self.serial and self.serial.is_open:
            self.serial.close()
            self.serial = None

    def is_open(self) -> bool:
        return self.serial is not None and self.serial.is_open

    def send_command(self, cmd: str) -> str:
        """
        Send a command terminated with CR and read the CR-delimited reply.

        Args:
            cmd: ASCII command string (without CR)

        Returns:
            The reply string stripped of whitespace

        Raises:
            serial.SerialException: on I/O errors
            TimeoutError: if no data received within timeout
        """
        if not self.serial or not self.serial.is_open:
            raise serial.SerialException("Serial port not open")

        # Send: command + CR
        cmd_bytes = cmd.encode('ascii') + b'\r'
        self.serial.write(cmd_bytes)
        self.serial.flush()

        # Read until CR or timeout (read(1) returns b'' on timeout)
        buffer = bytearray()
        while True:
            byte = self.serial.read(1)
            if byte == b'\r' or byte == b'':
                break
            buffer.extend(byte)

        if not buffer:
            raise TimeoutError("No data received (timeout)")

        return buffer.decode('ascii').strip()

    def expect_ok(self, cmd: str) -> bool:
        """
        Send a command and verify the OK00 reply.

        Returns:
            True if reply starts with 'OK00', False otherwise
        """
        try:
            reply = self.send_command(cmd)
            return reply.startswith('OK00')
        except (serial.SerialException, TimeoutError):
            return False

    def parse_measurement(self, reply: str) -> Optional[dict]:
        """
        Parse MES,1 reply: OK00,P1,0,{x},{y},{lv},...

        Args:
            reply: Raw reply string

        Returns:
            Dict with keys x, y, lv or None on parse failure
        """
        if not reply.startswith('OK00'):
            return None
        parts = reply.split(',')
        if len(parts) < 6:
            return None
        try:
            return {
                'x': float(parts[3]),
                'y': float(parts[4]),
                'lv': float(parts[5]),
            }
        except (ValueError, IndexError):
            return None

    @staticmethod
    def scan_ports() -> list[str]:
        """
        Scan available serial ports and return those matching CA-410 keywords.

        Matches ports whose description/name contains:
          - "Measuring Instruments"
          - "USB 串行设备"

        Uses try/except for maximum compatibility across pyserial versions.
        """
        keywords = ['Measuring Instruments', 'USB 串行设备']
        matches = []
        for port in serial.tools.list_ports.comports():
            # Try to get port name/description using try/except (safest approach)
            name = None
            for attr in ('description', 'descriptive_port_name', 'name'):
                try:
                    val = getattr(port, attr, None)
                    if val:
                        name = str(val)
                        break
                except Exception:
                    pass
            # Fallback: use device name directly
            if not name:
                try:
                    name = str(port.device)
                except Exception:
                    name = str(port)
            # Match keywords
            try:
                if any(kw in name for kw in keywords):
                    matches.append(port.device)
            except Exception:
                pass
        return matches
