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
        print(f"\n===============================")
        print(f"=== Testing {name} ===")
        print("===============================")
        ip = Uad()
        ip.inst = name

        # --- Enable / Disable Test ---
        ip.reset()
        ip.enable()
        print("\n--- Enable / Disable Test ---")
        enabled = ip.is_filter_enabled()
        print("Filter enabled:", enabled)

        ip.disable()
        enabled = ip.is_filter_enabled()
        print("Filter disabled:", enabled)

        ip.reset()
        ip.enable()

        # --- Bypass Test ---
        print("\n--- Bypass Test ---")
        ip.set_bypass(True)
        test_input = 0x1234
        output = ip.drive_signal(test_input)
        output_str = f"0x{output:X}" if output is not None else "Error"
        print(f"Input {hex(test_input)} → Output {output_str} (bypass)")
        ip.set_bypass(False)
        csr_after_bypass = ip.read_CSR()
        print(f"CSR after bypass cleared: 0x{csr_after_bypass:X}" if csr_after_bypass is not None else "CSR read failed")

        # --- Buffer / Halt Test ---
        print("\n--- Buffer / Halt Test ---")
        ip.halt()
        print("Filter halted:", ip.is_halted())
        # Feed 256 samples without printing each one
        for i in range(256):
            ip.drive_signal(i)
        print("Buffer count after 256 inputs:", ip.buffer_count())
        print("Overflow status:", ip.has_overflowed())
        ip.clear_buffer()
        print("Buffer cleared")
        print("Buffer count after clear:", ip.buffer_count())
        print("Overflow after clear:", ip.has_overflowed())

        # --- Register Read/Write Test ---
        print("\n--- Register Read/Write Test ---")
        coef_addr = 0x4
        new_coef = 0x12345678
        ip.write_register(coef_addr, new_coef)
        read_back = ip.read_register(coef_addr)
        print(f"Wrote {hex(new_coef)} → Read back: 0x{read_back:X}" if read_back is not None else "Read failed")

if __name__ == "__main__":
    run_tests()
