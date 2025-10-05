<!--suppress HtmlDeprecatedAttribute-->
<div align="center">
   <h1>🏹 Netapult</h1>
</div>

<hr />

<div align="center">

[💼 Purpose](#purpose) | [🏁 Usage](#usage)

</div>

<hr />

# Purpose

Netapult is a framework for querying and managing terminal-based devices without requiring software installation on 
targets, designed for network and security engineers to automate workflows involving the configuration or auditing of 
devices.

The framework is designed to execute human-readable commands for deployments where commands may rapidly change or where
a machine-to-machine protocol is not available. Through offering a plugin approach to protocols and device-specific
implementations, Netapult offers the ability for developers to easily integrate their own features without waiting for
a vendor.

### Use Cases

<details style="border: 1px solid; border-radius: 8px; padding: 8px; margin-top: 4px;">
<summary>🤖 Network Automation and Orchestration</summary>

Automate repetitive tasks such as configuration management, asset inventorying, and compliance checking.

</details>

<details style="border: 1px solid; border-radius: 8px; padding: 8px; margin-top: 4px;">
<summary>🛡️ Device Auditing and Hardening</summary>

Acquire device information at scale to enable environment-aware risk management.

</details>

<details style="border: 1px solid; border-radius: 8px; padding: 8px; margin-top: 4px;">
<summary>📚 Training</summary>

Rapidly configure a lab environment for trainees or validate their configuration.

</details>

Netapult is ideal for situations where a dedicated machine-to-machine protocol is not available as it provides an 
interface to execute raw commands, automating the workflow a human would undergo.

For systems where a machine-to-machine protocol is available (such as NETCONF or the Simple Network Management Protocol) 
combined with a use case that does not require quick command modification, you may find the following alternatives
more suitable:

- [ncclient](https://pypi.org/project/ncclient/): NETCONF client
  - [JunOS PyEZ](https://pypi.org/project/junos-eznc/): JunOS-specific wrapper
- [pyGNMI](https://pypi.org/project/pygnmi/): gRPC Network Management Interface client
- [requests](https://pypi.org/project/requests/): HTTP client for RESTCONF

Vendors may also offer products specific to their product suite. 

When these protocols or services are not available, such as during initial configuration, Netapult may aid setup and 
automate tasks that would otherwise mandate human intervention.

# Usage

As the framework does not provide any protocol or device-specific implementation, additional packages are required to 
efficiently use netapult. For example, to integrate an SSH capabilities, 
[netapult-ssh](https://pypi.org/project/netapult-ssh/) is available and offered as an extra dependency.

The following example leverages [netapult-ssh](https://pypi.org/project/netapult-ssh/) to execute a command and retrieve 
its response:

```python
import time

import netapult

with netapult.dispatch(
    "generic", # Use the generic client
    "ssh", # Use our SSH protocol
    protocol_options={
        "host": "your-host-here",
        "username": "your-username-here",
        "password": "your-password-here",
    },
) as client:
    # Allow time for the terminal to initialize
    time.sleep(3)

    # Acquire the banner
    banner: str = client.read(text=True)
    prompt_found, result = client.run_command("echo Hello World\n", text=True)

    print("Banner:", banner)
    print("Result:", result)
```

Across protocols, command execution generally remains in a consistent format. However, protocols may require different
options to establish a connection such as when authentication or a remote connection is required. Additionally,
device-specific implementations may offer an enhanced API, such as for switching in and out of modes 
(ex. privileged and configuration mode).