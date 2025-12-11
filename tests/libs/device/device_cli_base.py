import fcntl
import struct
import termios
from abc import ABC, abstractmethod

"""
Abstract class for device CLI client
Implementation for the CLI client can either use SSH or Serial console
"""


class DeviceCliClient(ABC):
    def __init__(self, device_ip, debug=False):
        self.device_ip = device_ip
        self.debug = debug

    @abstractmethod
    def connect(self, timeout=60) -> None:
        """
        Connect to the device.

        Args:
            timeout: Connection timeout in seconds

        Raises:
            DeviceConnectionError: If connection fails
            DeviceAuthenticationError: If authentication fails
            DeviceTimeoutError: If connection times out
        """
        pass

    @abstractmethod
    def wait_for_disconnect(self, timeout=600):
        """
        Wait for the device to disconnect.

        Args:
            timeout: Timeout in seconds to wait for disconnect
        """
        pass

    @abstractmethod
    def is_connected(self) -> bool:
        """
        Check if the device is connected.

        Returns:
            True if connected, False otherwise
        """
        pass

    @abstractmethod
    def close(self):
        """Close the connection to the device."""
        pass

    @abstractmethod
    def run_cmd(self, cmd) -> str:
        """
        Run a command on the device.

        Args:
            cmd: Command to run

        Returns:
            Command output

        Raises:
            DeviceNotConnectedError: If device is not connected
            DeviceCommandError: If command execution fails
            DeviceTimeoutError: If command times out
        """
        pass

    @abstractmethod
    def run_cmd_nonblocking(self, cmd) -> None:
        """
        Run a command on the device in the background.

        Args:
            cmd: Command to run

        Raises:
            DeviceNotConnectedError: If device is not connected
            DeviceCommandError: If command execution fails
        """
        pass

    @abstractmethod
    def run_cmd_with_input(self, cmd, input) -> str:
        """
        Run a command on the device with input.

        Args:
            cmd: Command to run
            input: Input to provide to the command

        Returns:
            Command output

        Raises:
            DeviceNotConnectedError: If device is not connected
            DeviceCommandError: If command execution fails
            DeviceTimeoutError: If command times out
        """
        pass

    @abstractmethod
    def interact(self):
        """
        Start an interactive session with the device.

        Raises:
            DeviceConnectionError: If connection fails
            DeviceCommandError: If interaction fails
        """
        pass

    def get_termsize(self):
        """Get terminal window size (rows, cols)."""
        try:
            rows, cols, _, _ = struct.unpack(
                "HHHH", fcntl.ioctl(0, termios.TIOCGWINSZ, struct.pack("HHHH", 0, 0, 0, 0))
            )
        except (OSError, ValueError, struct.error):
            # OSError: ioctl failed (not a terminal)
            # ValueError: invalid arguments
            # struct.error: unpack failed
            rows, cols = 0, 0
        return rows, cols
