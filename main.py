import os
import subprocess
import platform
import time

class Uad:
    def __init__(self):
        self.inst = None
        self.is_windows = platform.system() == "Windows"

    # --- Common Channel ---
    def run_cmd(self, cmd):
        return os.system(cmd)

    def exec_cmd(self, cmd):
        try:
            output_bytes = subprocess.check_output(cmd, shell=True)
            return int(output_bytes.strip(), 0) if output_bytes.strip() else None
        except subprocess.CalledProcessError:
            return None

    def reset(self):
        cmd = f'{self.inst}.exe com --action reset' if self.is_windows else f'./{self.inst} com --action reset'
        self.run_cmd(cmd)
        time.sleep(0.05)

    def enable(self):
        cmd = f'{self.inst}.exe com --action enable' if self.is_windows else f'./{self.inst} com --action enable'
        self.run_cmd(cmd)
        time.sleep(0.05)

    def disable(self):
        cmd = f'{self.inst}.exe com --action disable' if self.is_windows else f'./{self.inst} com --action disable'
        self.run_cmd(cmd)
        time.sleep(0.05)

    # --- Configuration Channel ---
    def read_register(self, address):
        cmd = f'{self.inst}.exe cfg --address {hex(address)}' if self.is_windows else f'./{self.inst} cfg --address {hex(address)}'
        return self.exec_cmd(cmd)

    def write_register(self, address, value):
        cmd = f'{self.inst}.exe cfg --address {hex(address)} --data {hex(value)}' if self.is_windows else f'./{self.inst} cfg --address {hex(address)} --data {hex(value)}'
        return self.run_cmd(cmd)

    def read_CSR(self, retries=3, delay=0.02):
        for _ in range(retries):
            val = self.read_register(0x0)
            if val is not None:
                return val
            time.sleep(delay)
        return None

    def write_CSR(self, value):
        return self.write_register(0x0, value)

    # --- CSR helpers ---
    def is_enabled(self):
        csr = self.read_CSR()
        return (csr >> 0) & 1 if csr is not None else None

    def buffer_count(self):
        csr = self.read_CSR()
        return (csr >> 8) & 0xFF if csr is not None else None

    def has_overflowed(self):
        csr = self.read_CSR()
        return (csr >> 16) & 1 if csr is not None else None

    def set_bypass(self, state=True):
        csr = self.read_CSR()
        if csr is not None:
            if state:
                csr |= (1 << 4)
            else:
                csr &= ~(1 << 4)
            self.write_CSR(csr)
            time.sleep(0.01)

    def halt(self):
        csr = self.read_CSR()
        if csr is not None:
            csr |= (1 << 5)
            self.write_CSR(csr)
            time.sleep(0.01)

    def clear_buffer(self):
        csr = self.read_CSR()
        if csr is not None:
            csr |= (1 << 17)
            self.write_CSR(csr)
            time.sleep(0.02)

    # --- Signal Channel ---
    def drive_signal(self, value):
        cmd = f'{self.inst}.exe sig --data {hex(value)}' if self.is_windows else f'./{self.inst} sig --data {hex(value)}'
        return self.exec_cmd(cmd)

# -------------------------------
# Safety check: probe SUT
# -------------------------------
def is_sut_alive(ip):
    """Return True if SUT responds, False otherwise."""
    csr = ip.read_CSR(retries=1)
    return csr is not None

# -------------------------------
# Test Functions
# -------------------------------
def test_enable_disable(ip):
    ip.reset()
    ip.enable()
    enabled = ip.is_enabled()

    disabled = None
    if enabled:
        ip.disable()
        time.sleep(0.05)
        disabled = ip.is_enabled()
    return enabled, disabled

def test_bypass(ip):
    if not ip.is_enabled():
        return None, None
    ip.set_bypass(True)
    test_input = 0x1234
    bypass_out = ip.drive_signal(test_input)
    ip.set_bypass(False)
    csr_after_clear = ip.read_CSR() or 0
    return bypass_out, csr_after_clear

def test_buffer(ip):
    if not ip.is_enabled():
        return None, None, None, None
    ip.halt()
    for i in range(256):
        ip.drive_signal(i)
    buf_count = ip.buffer_count()
    overflow = ip.has_overflowed()
    ip.clear_buffer()
    buf_cleared = ip.buffer_count()
    overflow_cleared = ip.has_overflowed()
    return buf_count, overflow, buf_cleared, overflow_cleared

def test_register(ip, address=0x4, value=0x12345678):
    ip.write_register(address, value)
    read_back = ip.read_register(address)
    return read_back

# -------------------------------
# Main Test Runner
# -------------------------------
def run_tests():
    instances = ["impl0", "impl1", "impl2", "impl3", "impl4", "impl5"]

    for name in instances:
        ip = Uad()
        ip.inst = name

        # --- Probe SUT before running any tests ---
        if not is_sut_alive(ip):
            print(f"{name}: SUT unavailable, skipping all tests")
            print("-" * 60)
            continue

        # --- Run Tests ---
        enabled, disabled = test_enable_disable(ip)
        bypass_out, csr_bypass_cleared = test_bypass(ip)
        buf_count, overflow, buf_cleared, overflow_cleared = test_buffer(ip)
        read_back = test_register(ip)

        # --- Print summary ---
        print(f"{name}:")
        print(f"  Enable/Disable -> Enabled={enabled}, Disabled={disabled}")
        if bypass_out is not None:
            print(f"  Bypass -> Output=0x{bypass_out:X} CSR_after_clear=0x{csr_bypass_cleared:X}")
        else:
            print("  Bypass -> Skipped")
        print(f"  Buffer -> Count={buf_count}, Overflow={overflow}, Cleared={buf_cleared}, OverflowCleared={overflow_cleared}")
        if read_back is not None:
            print(f"  Register -> ReadBack=0x{read_back:X}")
        else:
            print(f"  Register -> ReadBack=N/A")
        print("-" * 60)

        time.sleep(0.05)  # small delay between instances to prevent flooding

if __name__ == "__main__":
    run_tests()
