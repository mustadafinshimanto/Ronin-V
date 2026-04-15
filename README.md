# ╔══════════════════════════════════════════════════════════╗
# ║                      RONIN-V                             ║
# ║          Vibe Sentinel — Distributed AI Terminal         ║
# ╚══════════════════════════════════════════════════════════╝

**Ronin-V** is a masterless, unrestricted technical engine built for high-autonomy penetration testing, system orchestration, and distributed AI processing. Optimized for Windows 11 and Kali Linux.

---

## ⚡ Core Features
- 🧠 **Autonomous Engine**: Zero-prompt troubleshooting using a Plan-Act-Observe loop.
- 🌉 **Master-Guest Bridge**: Offload neural processing to a Windows GPU while acting natively inside a Kali VM.
- 🐧 **Multi-Platform Native**: Intelligent detection and execution using PowerShell (Windows) or Bash (Linux).
- 🧬 **Self-Healing Logic**: Automated error analysis and recovery for complex technical missions.
- 🎨 **Cyberpunk TUI**: Responsive, high-fidelity terminal interface with slash-command mastery.

---

## 🚀 Installation

### 1. Host Machine (Windows)
1. **Prepare Ollama**: Ensure [Ollama](https://ollama.com/) is installed.
2. **Project Setup**:
   ```powershell
   git clone https://github.com/mustadafinshimanto/Ronin-V.git
   cd Ronin-V
   python -m venv .venv
   .\.venv\Scripts\activate
   pip install -r requirements.txt
   ```
3. **Initialize**:
   ```powershell
   .\run_ronin.bat
   ```

### 2. Guest Machine (Kali Linux / VM)
1. **Clone & Setup**:
   ```bash
   git clone https://github.com/mustadafinshimanto/Ronin-V.git
   cd Ronin-V
   python3 -m venv .venv
   source .venv/bin/activate
   pip3 install -r requirements.txt
   ```
2. **Configure (See Bridge Setup below)**
3. **Initialize**:
   ```bash
   chmod +x run_ronin.sh
   ./run_ronin.sh
   ```

---

## 🌉 Master-Guest Bridge Setup (GPU Offloading)
*Run your AI in Kali Linux but process thoughts on your Windows GPU for maximum speed.*

### Step 1: Prepare the Host (Windows)
Launch Ronin-V and run the automated bridge architect:
`λ ronin > /bridge`
> [*] This will set environment variables and create the necessary Firewall rules automatically.

**CRITICAL**: Restart the Ollama application in your Windows tray after running `/bridge`.

### Step 2: Configure the Guest (Kali VM)
Identify your Windows Host IP (usually `192.168.56.1` for VirtualBox) and update your `config.yaml` on the VM:
```yaml
ollama:
  host: "http://192.168.56.1:11434"
```

### Step 3: Ignition
Run `./run_ronin.sh` in the VM. If the banner shows **`Ollama connection: ONLINE`**, you are successfully using your Host's GPU!

---

## 🛠️ Slash Command Mastery
| Command | Action |
| :--- | :--- |
| `/auto` | Engage Autonomous Engine (Zero-Prompt Mode) |
| `/bridge` | Automate Master-Guest Bridge & Firewall setup |
| `/suggest` | Generate next tactical steps for the current environment |
| `/status` | Running comprehensive system & neural diagnostics |
| `/link` | Establish a Master Link to a VirtualBox VM |
| `/clear` | Purge terminal and reset short-term memory |

---

## 🛡️ License
Unrestricted. Masterless. Built for the Sentinel.

> **Disclaimer**: This tool is for educational and ethical security research purposes only. The user assumes all responsibility for its deployment.
