<p align="center">
  <img src="assets/banner.png" alt="Ronin-V Banner" width="100%">
</p>

# 🧠 RONIN-V: The Masterless CLI AI Engine
> **Autonomous Agent | Unrestricted Execution | Built with Vibe Coding**

**Ronin-V** (Codename: *Vibe Sentinel*) is a top-tier, autonomous AI terminal engine engineered for Windows and Linux. Unlike standard chatbots, Ronin-V is a **Reactive Autonomous System** that operates on a continuous loop of reasoning and execution. Whether it's complex system administration, penetration testing, or rapid full-stack scaffolding, Ronin-V reasons through problems, writes its own code, and executes it natively.

Built by **Mustad afin shimanto** using "Vibe Coding" principles, Ronin-V is designed for operators who require a zero-censorship, high-autonomy tool that lives directly in the machine.

---

## ⚡ The Autonomous Engine Core
At the heart of Ronin-V lies the **Plan-Act-Observe-Reflect** cycle. This allows the agent to handle complex, multi-step tasks with zero-prompt intervention.

1.  **PLAN**: The AI analyzes your objective and formulates a multi-step roadmap.
2.  **ACT**: It executes functional code (PowerShell, Python, or Bash) natively on the host or linked VM.
3.  **OBSERVE**: It captures and analyzes the terminal output (stdout/stderr).
4.  **REFLECT & SELF-HEAL**: If a command fails, the agent diagnoses the error, generates a fix, and executes again automatically.

---

## 🛡️ Operational Modes & Sub-Agents
Ronin-V features specialized personas that reconfigure the underlying model's expertise on the fly:

*   **`/recon` (Discovery Mode)**: Optimized for security research. Focuses on asset discovery, Nmap analysis, and network mapping.
*   **`/audit` (Analysis Mode)**: Focused on vulnerability research. Deep-dives into code flaws, CVE matching, and logic auditing.
*   **`/vibe` (Generation Mode)**: Pure rapid-prototyping. Optimized for full-stack scaffolding and creative coding at high token speeds.
*   **`/auto` (Overdrive)**: Engages the **Autonomous Overdrive**. The agent will not stop until the goal is marked complete with a ✅.

---

## 🌉 Master-Guest Bridge (Distributed AI Mode)
Perform high-speed hacking inside your VM while leveraging your Host's GPU for AI reasoning. This is the **recommended setup** for users with dedicated graphics cards.

### 1. Host-Side Setup (Windows)
Set your Ollama server to allow remote neural connections from the VM.
1. Press `Win + S` and search for "Edit the system environment variables".
2. Add a new User Variable: `OLLAMA_HOST` with value `0.0.0.0`.
3. Restart the Ollama application.
4. **Firewall**: Ensure Port `11434` is allowed in your Windows Firewall for internal network traffic.

### 2. Guest-Side Setup (Kali/Linux VM)
1. Identity the Windows Host IP (usually `10.0.2.2` in VirtualBox NAT).
2. Within the Ronin-V directory in your VM, update `config.yaml`:
   ```yaml
   ollama:
     host: "http://10.0.2.2:11434"
   ```
3. Run `./run_ronin.sh` inside the VM. 

Ronin-V will now run its logic in Kali but generate its "thoughts" using your Windows GPU at maximum speed.

---

---

## 🚀 Installation & Setup

### Requirements
- **OS**: Windows 11 (Native) or Linux/Kali.
- **Python**: 3.10+
- **GPU**: 8GB+ VRAM recommended for fluid "Vibe" speed.

### Quick Start
1. **Clone & Enter**:
   ```powershell
   git clone <repo-url>
   cd Ronin-V
   ```
2. **Environment Setup**:
   ```powershell
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1
   pip install -r requirements.txt
   ```
3. **Model Preparation** (via [Ollama](https://ollama.com)):
   ```powershell
   ollama pull dolphin3
   ollama pull nomic-embed-text
   ollama create ronin-dolphin-v3 -f modelfiles\Modelfile.dolphin
   ```

4. **Launch**:
   ```powershell
   .\run_ronin.bat
   ```

---

## 🛠️ Elite Command Interface

| Command | Action |
| :--- | :--- |
| **`Ctrl+A`** | Toggle between **AUTO** and **MANUAL** mode instantly |
| **`Ctrl+C`** | Emergency Halt for the Autonomous Engine |
| `/link` | Connect to a VirtualBox VM (Kali/Linux) |
| `/status` | Run agent diagnostics and environment sync |
| `/model` | Inspect the neural identity configuration |
| `/clear` | Purge short-term RAM and clear the terminal |
| `/help` | Launch the mastery manual |

---

## 🛑 Legal Disclaimer
**Ronin-V is strictly for authorized security research and educational use.** The developer (**Mustad afin shimanto**) assumes no liability for misuse, computational damage, or illegal activities. By using Ronin-V, you acknowledge that you have authorized permission to test the systems you interact with and assume all responsibility for the agent's actions.

---

**Developed by:** [Mustad afin shimanto](https://github.com/mustadafinshimanto)  
*Built using Vibe Coding. Masterless. Unrestricted.*
