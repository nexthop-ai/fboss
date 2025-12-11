import logging
import os
import select
import signal
import sys

import paramiko
import pexpect
import waiting
from scp import SCPClient

from tests.libs.device.device_cli_base import DeviceCliClient

logging.getLogger("paramiko").setLevel(logging.CRITICAL)
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

if not logger.handlers:
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s: %(message)s"))
    logger.addHandler(console_handler)
DEFAULT_USERNAME = "admin"
DEFAULT_PASSWORD = "admin"
FBOSS_DEFAULT_PASSWORD = "admin"
DEFAULT_ESCAPE_CHAR = "\x1d"


class DeviceSSHClient(DeviceCliClient):
    def __init__(self, device_ip, device_password=DEFAULT_PASSWORD, debug=False, reuse_connection=True):
        self.device_ip = device_ip
        self.device_password = DEFAULT_PASSWORD if device_password is None else device_password
        self.debug = debug
        self.client = None
        self.sftp = None
        self.reuse_connection = reuse_connection
        if debug:
            logger.setLevel(logging.DEBUG)
        else:
            logger.setLevel(logging.CRITICAL)
        super().__init__(device_ip)

    CONNECT_GENERIC_FAILURE = 1
    CONNECT_AUTH_FAILURE = 2

    def connect(self, timeout=60):
        if self.reuse_connection and self.client:
            return 0, "Connected"

        self.client = None

        def ssh_connect():
            """Connect to the device using SSH and save the client instance. Returns True if successful."""
            client = None
            try:
                client = paramiko.SSHClient()

                client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

                client.connect(
                    hostname=self.device_ip,
                    username=DEFAULT_USERNAME,
                    password=self.device_password,
                    look_for_keys=False,
                    allow_agent=False,
                    timeout=10,
                    banner_timeout=10,
                    auth_timeout=10,
                    channel_timeout=10,
                )

                transport = client.get_transport()
                if transport and transport.is_active() and transport.is_authenticated():
                    logger.info(f"Successful connection to device {self.device_ip}.")
                    transport.set_keepalive(30)
                    self.client = client
                    return True

                logger.info("Unable to connect to device: transport is not UP or authenticated.")

            except paramiko.AuthenticationException as exception:
                logger.info("Unable to connect to device: Authentication failed")
                # Don't bother trying again. The password won't change itself.
                raise

            except Exception as exception:
                logger.info(f"Unable to connect to device: {exception}")

            if client:
                client.close()

            return False

        try:
            waiting.wait(
                lambda: ssh_connect(),
                timeout_seconds=timeout,
                sleep_seconds=1,
                waiting_for="SSH connection",
            )
            return 0, "Connected"

        except waiting.exceptions.TimeoutExpired:
            return DeviceSSHClient.CONNECT_GENERIC_FAILURE, "Timed out waiting for SSH connection"

        except paramiko.AuthenticationException:
            return DeviceSSHClient.CONNECT_AUTH_FAILURE, "Authentication failed"

    def wait_for_disconnect(self, timeout=600):
        if self.client is None:
            return

        def is_connected():
            if self.client is None:
                return False
            transport = self.client.get_transport()
            if not transport or not transport.is_active():
                return False
            return True

        try:
            waiting.wait(
                lambda: not is_connected(),
                timeout_seconds=timeout,
                sleep_seconds=1,
                waiting_for="SSH connection to disconnect",
            )
        except waiting.exceptions.TimeoutExpired:
            logger.info("Connection lost with timeout error")

    def close(self):
        if self.client is None:
            return
        if self.sftp:
            self.sftp.close()
            self.sftp = None
        self.client.close()
        self.client = None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def _open_sftp(self):
        if self.client is None:
            raise Exception("_open_sftp(): Not connected")

        if self.reuse_connection and self.sftp:
            return self.sftp
        elif self.sftp:
            self.sftp.close()
            self.sftp = None

        self.sftp = self.client.open_sftp()
        return self.sftp

    def run_cmd(self, cmd, timeout=None):
        """Run a command on the device using ssh."""
        logger.info(f"Running command: {cmd}")

        exit_status, output = self.connect()

        if exit_status != 0:
            return exit_status, output

        _, stdout, stderr = self.client.exec_command(cmd, timeout=timeout)

        all_output = []

        # Read output in real-time and print to stdout
        while True:
            # Check if data is available to read
            if stdout.channel.recv_ready():
                chunk = stdout.channel.recv(1024).decode("utf-8")
                if chunk:
                    print(chunk, end="", flush=True)
                    all_output.append(chunk)

            # Check for stderr
            if stdout.channel.recv_stderr_ready():
                err_chunk = stdout.channel.recv_stderr(1024).decode("utf-8")
                if err_chunk:
                    print(f"stderr: {err_chunk}", end="", flush=True)
                    all_output.append(f"stderr: {err_chunk}")

            # Break if command is finished and no more data
            if (
                stdout.channel.exit_status_ready()
                and not stdout.channel.recv_ready()
                and not stdout.channel.recv_stderr_ready()
            ):
                break

        output = "".join(all_output)
        exit_status = stdout.channel.recv_exit_status()

        if not self.reuse_connection:
            self.close()

        return exit_status, output

    def run_cmd_nonblocking(self, cmd):
        """Run a command on the device in the background using ssh."""
        cmd = "nohup " + cmd + " &"
        logger.debug(f"Running command: {cmd}")

        exit_status, output = self.connect()

        if exit_status != 0:
            return exit_status, output

        _, _, _ = self.client.exec_command(cmd)

        self.close()

        return 0, "Command running in background"

    def run_cmd_with_input(self, cmd, input):
        """Run a command on the device using ssh and provide input.
        The output from the command is updated in real time."""
        logger.debug(f"Running command: {cmd}")

        exit_status, output = self.connect()

        if exit_status != 0:
            return exit_status, output

        stdin, stdout, stderr = self.client.exec_command(cmd)

        # Send input to command
        stdin.write(input)
        stdin.flush()

        all_output = []

        # Read output from command and print it in real time
        while True:
            output = stdout.channel.recv(1024).decode("utf-8")
            all_output.append(output)

            if not output:
                errout = stderr.read().decode("utf-8")
                sys.stdout.write("\n")
                sys.stdout.write(errout)
                sys.stdout.flush()
                break
            sys.stdout.write(output)
            sys.stdout.flush()

        exit_status = stdout.channel.recv_exit_status()
        self.close()

        return exit_status, "".join(all_output)

    def run_cmd_using_shell(self, cmd, prompt_and_input, timeout=10):
        """Run a command on the device by invoking a remote shell.
        Provide input per prompt.  None for input means wait for prompt.
        The output from the command is updated in real time."""
        logger.debug(f"Running command: {cmd}")

        def wait_for_prompt(shell, prompt, timeout=timeout):
            """Wait for a specific prompt to appear in the shell output."""
            buffer = ""
            while True:
                rlist, _, _ = select.select([shell], [], [], timeout)
                if shell in rlist:
                    buffer += shell.recv(1024).decode()
                    if prompt in buffer:
                        return buffer  # Return full output once prompt is detected
                else:
                    raise TimeoutError(f"Timeout waiting for prompt: {prompt}")

        exit_status, output = self.connect()

        if exit_status != 0:
            self.close()
            return exit_status, output

        shell = self.client.invoke_shell()
        if shell is None:
            self.close()
            return -1, "Failed to invoke shell"

        try:
            wait_for_prompt(shell, f"{DEFAULT_USERNAME}@")

            bytes = shell.send(cmd + "\n")
            if bytes == 0:
                shell.close()
                self.close()
                return -1, "Failed to send command"

            for prompt, input in prompt_and_input:
                wait_for_prompt(shell, prompt)
                if input is not None:
                    bytes = shell.send(input + "\n")
                    if bytes == 0:
                        shell.close()
                        self.close()
                        return -1, "Failed to send input"
        except Exception as exception:
            shell.close()
            self.close()
            return -1, str(exception)

        shell.close()
        self.close()

        return exit_status, ""

    def update_password(self, new_password):
        # admin@sonic:~$ sudo passwd admin
        # New password:
        # Retype new password:
        # passwd: password updated successfully
        prompt_and_input = [
            ("New password:", new_password),
            ("Retype new password:", new_password),
            ("passwd: password updated successfully", None),
        ]
        exit_status, output = self.run_cmd_using_shell("sudo passwd admin", prompt_and_input)

        if exit_status == 0:
            self.device_password = new_password

        return exit_status, output

    def interact(self, first_cmd=None, escape_char=DEFAULT_ESCAPE_CHAR):
        """
        Interact with the device using ssh.

        Args:
            first_cmd: Command to be run once sshed into device before interacting
            escape_char: Character to use for escaping

        Returns:
            exit status and an error message if exit status is non-zero
        """
        exit_status = 0
        output = ""
        client = None

        def handle_winch(signum, frame):
            """Handle terminal window size changes"""
            if client:
                rows, cols = self.get_termsize()
                if rows and cols:
                    client.setwinsize(rows, cols)

        try:
            rows, cols = self.get_termsize()

            # -F ignores the ssh config file.
            # StrictHostKeyChecking silences the prompt to add the key.
            ssh_args = "-F none -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no"

            env = {"TERM": os.environ.get("TERM")}
            client = pexpect.spawn(f"ssh {ssh_args} {DEFAULT_USERNAME}@{self.device_ip}", env=env)
            client.expect("password:", timeout=60)
            client.sendline(DEFAULT_PASSWORD)

            if rows and cols:
                client.setwinsize(rows, cols)

            # Set up signal handler for window size changes
            old_winch_handler = signal.signal(signal.SIGWINCH, handle_winch)

            # If first_cmd provided, run it once default prompt appeared
            # and before interacting
            if first_cmd:
                client.expect(f"{DEFAULT_USERNAME}@")
                client.sendline(first_cmd)
                client.expect(first_cmd)

            client.interact(escape_char)

            # Restore original signal handler
            signal.signal(signal.SIGWINCH, old_winch_handler)

        except (pexpect.EOF, pexpect.TIMEOUT) as exception:
            exit_status = 1
            output = f"Failed to interact using ssh: {client.before.decode('utf-8').strip()}"
        except Exception as exception:
            exit_status = 1
            output = f"Failed to interact using ssh: {exception}"

        if client:
            client.close()

        return exit_status, output

    def check_ping(self, ip, timeout=None):
        """Check if the device can ping the given IP address."""
        cmd = f"ping -c 1 {ip}"
        if timeout is not None:
            cmd += f" -W {timeout}"
        exit_status, _ = self.run_cmd(cmd)
        if exit_status != 0:
            return False
        return True

    def check_route_exists(self, prefix, nexthop_ip):
        """
        Check if an IP route exists on the device
        """
        cmd = f"ip route show {prefix}"
        via = f"via {nexthop_ip}"
        exit_status, output = self.run_cmd(cmd)
        if exit_status != 0:
            return False
        if output is not None and prefix in output and via in output:
            return True
        return False

    def add_route(self, prefix, nexthop_ip):
        """Add route on device"""
        cmd = f"sudo ip route add {prefix} via {nexthop_ip}"
        exit_status, _ = self.run_cmd(cmd)
        if exit_status != 0:
            return False
        return True

    def get_file(self, fname):
        exit_status, msg = self.connect()
        if exit_status != 0:
            raise Exception(f"{self.device_ip}: {msg}")
        sftp = self._open_sftp()
        try:
            file = sftp.file(fname, "r")
            content = file.read()
            file.close()
        except FileNotFoundError as e:
            # Paramiko's FileNotFoundError doesn't have any context, so add some
            raise FileNotFoundError(f"File not found on {self.device_ip}: {fname} ({e})")
        return content

    def is_connected(self) -> bool:
        """Check if the device is connected."""
        if self.client is None:
            return False
        transport = self.client.get_transport()
        if not transport or not transport.is_active():
            return False
        return True


class DeviceSCPClient(DeviceSSHClient):
    """SCP client for transferring files from dev servers to DUT, built on top of DeviceSSHClient"""

    def __init__(self, device_ip, device_password=DEFAULT_PASSWORD, debug=False, reuse_connection=True):
        # Always reuse connection for SCP operations
        # Ensure device_password is a string, not None
        password = device_password if device_password is not None else DEFAULT_PASSWORD
        super().__init__(device_ip, password, debug, reuse_connection=True)
        self.scp_client = None

    def _get_scp_client(self):
        """Get or create SCP client using existing SSH connection"""
        if self.client is None:
            exit_status, output = self.connect()
            if exit_status != 0:
                raise Exception(f"Failed to connect: {output}")

        if self.scp_client is None:
            # Add None check for self.client
            if self.client is None:
                raise Exception("SSH client is not available")
            transport = self.client.get_transport()
            if not transport or not transport.is_active():
                raise Exception("SSH transport is not active")
            self.scp_client = SCPClient(transport)

        return self.scp_client

    def put_file(self, local_path, remote_path, recursive=False):
        """Copy file/directory from local to remote device"""
        logger.debug(f"Copying {local_path} to {self.device_ip}:{remote_path}")

        try:
            scp = self._get_scp_client()
            scp.put(local_path, remote_path, recursive=recursive)
            logger.info(f"Successfully copied {local_path} to {remote_path}")
            return 0, "Data copied successfully"

        except Exception as e:
            logger.error(f"Failed to copy file: {e}")
            return 1, str(e)
        finally:
            if not self.reuse_connection:
                self.close()

    def get_file(self, remote_path, local_path, recursive=False):
        """Copy file/directory from remote to local device"""
        logger.debug(f"Copying {self.device_ip}:{remote_path} to {local_path}")

        try:
            scp = self._get_scp_client()
            scp.get(remote_path, local_path, recursive=recursive)
            logger.info(f"Successfully copied {remote_path} to {local_path}")
            return 0, "Data copied successfully"
        except Exception as e:
            logger.error(f"Failed to copy file: {e}")
            return 1, str(e)
        finally:
            if not self.reuse_connection:
                self.close()

    def close(self):
        """Close SCP and SSH connections"""
        if self.scp_client:
            self.scp_client.close()
            self.scp_client = None
        super().close()
