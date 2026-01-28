import os
import subprocess
import platform

# Simple color codes for terminal
GREEN = '\033[92m'
RED = '\033[91m'
ENDC = '\033[0m'

class Uad():
    def __init__(self, inst):
        # Windows: use .exe, Linux/macOS: use ./inst
        if platform.system() == "Windows":
            self.inst = f"{inst}.exe"
        else:
            self.inst = f"./{inst}"

    def reset(self):
        os.system(f'{self.inst} com --action reset')

    def disable(self):
        os.system(f'{self.inst} com --action disable')

    def enable(self):
        os.system(f'{self.inst} com --action enable')

    def read_CSR(self):
        try:
            csr_bytes = subprocess.check_output(f'{self.inst} cfg --address 0x0', shell=True).decode().strip()
            return int(csr_bytes, 0)
        except subprocess.CalledProcessError as e:
            return None

def decode_flags(csr):
    if csr is None:
        return "read failed"
    flags = []
    if csr & 0x1: flags.append("ENABLE")
    if csr & 0x2: flags.append("BYPASS")
    if csr & 0x10000: flags.append("OVERFLOW")
    return ", ".join(flags) if flags else "NONE"

# List of IP instances
instances = ["impl0", "impl1", "impl2", "impl3", "impl4", "impl5"]

summary = []

for inst in instances:
    print(f"\n===== Testing {inst} =====")
    ip = Uad(inst)

    # 1. Enable / Disable
    ip.reset()
    ip.enable()
    csr_enabled = ip.read_CSR()
    print(f"CSR after enable: {hex(csr_enabled) if csr_enabled is not None else 'None'}")
    print(f"Decoded: {decode_flags(csr_enabled)}")

    ip.disable()
    print("Attempting CSR read after disable:")
    csr_disabled = ip.read_CSR()
    print(f"CSR after disable: {hex(csr_disabled) if csr_disabled is not None else 'None'}")
    print(f"Decoded: {decode_flags(csr_disabled)}")

    # Save for summary
    summary.append((inst, csr_enabled, decode_flags(csr_enabled), csr_disabled, decode_flags(csr_disabled)))

# Print summary table
print("\n===== SUMMARY (Windows) =====")
header = f"{'Instance':<8} {'CSR Enabled':<12} {'Decoded':<30} {'CSR Disabled':<12} {'Decoded':<30}"
print(header)
print("-" * len(header))

for row in summary:
    inst, en_val, en_dec, dis_val, dis_dec = row
    en_str = f"{hex(en_val) if en_val is not None else 'None'}"
    dis_str = f"{hex(dis_val) if dis_val is not None else 'None'}"
    print(f"{inst:<8} {en_str:<12} {en_dec:<30} {dis_str:<12} {dis_dec:<30}")

print("\n===== ALL TESTS COMPLETE =====")
