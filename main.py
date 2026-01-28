import os
import subprocess
import platform

class Uad:
    def __init__(self):
        self.inst = None
        self.is_windows = platform.system() == "Windows"

    # --- Common Channel ---
    def reset(self):
        cmd = f'{self.inst}.exe com --action reset' if self.is_windows else f'./{self.inst} com --action reset'
        return os.system(cmd)

    def enable(self):
        cmd = f'{self.inst}.exe com --action enable' if self.is_windows else f'./{self.inst} com --action enable'
        return os.system(cmd)

    def disable(self):
        cmd = f'{self.inst}.exe com --action disable' if self.is_windows else f'./{self.inst} com --action disable'
        return os.system(cmd)

    # --- Configuration Channel ---
    def read_CSR(self):
        cmd = f'{self.inst}.exe cfg --address 0x0' if self.is_windows else f'./{self.inst} cfg --address 0x0'
        try:
            csr_bytes = subprocess.check_output(cmd, shell=True)
            return int(csr_bytes.strip(), 0)
        except subprocess.CalledProcessError:
            return None

    def read_register(self, address):
        cmd = f'{self.inst}.exe cfg --address {hex(address)}' if self.is_windows else f'./{self.inst} cfg --address {hex(address)}'
        try:
            output = subprocess.check_output(cmd, shell=True)
            return int(output.strip(), 0)
        except subprocess.CalledProcessError:
            return None

    def write_register(self, address, value):
        cmd = f'{self.inst}.exe cfg --address {hex(address)} --data {hex(value)}' if self.is_windows else f'./{self.inst} cfg --address {hex(address)} --data {hex(value)}'
        return os.system(cmd)

    def write_CSR(self, value):
        return self.write_register(0x0, value)

    # --- CSR helpers ---
    def is_filter_enabled(self):
        csr = self.read_CSR()
        return (csr >> 0) & 1 if csr is not None else None

    def is_halted(self):
        csr = self.read_CSR()
        return (csr >> 5) & 1 if csr is not None else None

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

    def halt(self):
        csr = self.read_CSR()
        if csr is not None:
            csr |= (1 << 5)
            self.write_CSR(csr)

    def clear_buffer(self):
        csr = self.read_CSR()
        if csr is not None:
            csr |= (1 << 17)
            self.write_CSR(csr)

    # --- Signal Channel ---
    def drive_signal(self, value):
        cmd = f'{self.inst}.exe sig --data {hex(value)}' if self.is_windows else f'./{self.inst} sig --data {hex(value)}'
        try:
            output_bytes = subprocess.check_output(cmd, shell=True)
            return int(output_bytes.strip(), 0) if output_bytes.strip() else None
        except subprocess.CalledProcessError:
            return None

# -------------------------------
# Main Test Suite
# -------------------------------
def run_tests():
    instances = ["impl0", "impl1", "impl2", "impl3", "impl4", "impl5"]

    for name in instances:
        ip = Uad()
        ip.inst = name

        # --- Enable / Disable ---
        ip.reset()
        ip.enable()
        csr = ip.read_CSR()
        enabled = (csr >> 0) & 1 if csr else None

        ip.disable()
        csr = ip.read_CSR()
        disabled = (csr >> 0) & 1 if csr else None

        # --- Bypass ---
        ip.reset()
        ip.enable()
        ip.set_bypass(True)
        test_input = 0x1234
        bypass_out = ip.drive_signal(test_input)
        bypass_str = f"0x{bypass_out:X}" if bypass_out is not None else "Error"
        ip.set_bypass(False)
        csr = ip.read_CSR()
        csr_bypass_cleared = f"0x{csr:X}" if csr else "N/A"

        # --- Buffer / Halt ---
        ip.halt()
        for i in range(256):
            ip.drive_signal(i)
        csr = ip.read_CSR()
        buf_count = (csr >> 8) & 0xFF if csr else None
        overflow = (csr >> 16) & 1 if csr else None
        ip.clear_buffer()
        csr = ip.read_CSR()
        buf_cleared = (csr >> 8) & 0xFF if csr else None
        overflow_cleared = (csr >> 16) & 1 if csr else None

        # --- Register ---
        coef_addr = 0x4
        new_coef = 0x12345678
        ip.write_register(coef_addr, new_coef)
        read_back = ip.read_register(coef_addr)
        read_back_str = f"0x{read_back:X}" if read_back else "N/A"

        # --- Print summary ---
        print(
            f"{name}: Enabled={enabled}, Disabled={disabled}, "
            f"BypassOut={bypass_str}, CSR_bypass={csr_bypass_cleared}, "
            f"Buffer={buf_count}, Overflow={overflow}, "
            f"BufferCleared={buf_cleared}, OverflowCleared={overflow_cleared}, "
            f"RegReadBack={read_back_str}"
        )

if __name__ == "__main__":
    run_tests()
