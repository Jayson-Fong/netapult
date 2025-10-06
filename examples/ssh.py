"""
Secure Shell (SSH) Example

Requires: netapult[ssh]
"""

import getpass
import os
import time

import netapult

default_username: str = getpass.getuser()

with netapult.dispatch(
    "generic",  # Use the generic client
    "ssh",  # Use the SSH protocol provided by netapult-ssh
    protocol_options={
        "host": input("Host [localhost]: ") or "localhost",
        "username": input(f"Username [{default_username}]: ") or default_username,
        "password": getpass.getpass("Password: "),
    },
) as client:
    separator: str = "=" * os.get_terminal_size().columns

    # Allow time for the terminal to initialize
    time.sleep(3)
    banner: str = client.read(text=True)

    print(separator)
    print(banner)
    print(separator)

    command: str = input("Command: ")
    while command:
        prompt_found, result = client.run_command(command, text=True)

        print(separator)
        print(result)
        print(separator)

        command = input("Command: ")
