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

Netapult is a framework for querying and managing terminal-based devices, designed for developers requiring maximum 
control over workflows without abstracting away fine-grained control. Netapult enables the execution of commands against 
these terminal-based devices and the collection of resulting data.

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

# Usage

The framework does **not** ship with a protocol or device-specific implementations in an effort to provide a 
maintainable, plugin-like structure such that framework's package does not require updating to alter a protocol or 
device implementation.