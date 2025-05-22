#Flash_Hello
# Version 20250518.01 tested on MacOS

import os
import sys
import time
import threading
import subprocess
import tkinter as tk
from tkinter import messagebox, scrolledtext, ttk, font
import serial
import serial.tools.list_ports
import urllib.request

# === CONFIGURATION ===
BAUD = "921600"
CHIP = "esp32s3"

FIRMWARE_URLS = {
    "HelloDevice.ino.bin": "https://raw.githubusercontent.com/markleavitt/HelloDeviceFirmware/main/HelloDevice.ino.bin",
    "HelloCell.ino.bin": "https://raw.githubusercontent.com/markleavitt/HelloDeviceFirmware/main/HelloCell.ino.bin"
}

FLASH_MAP_WIFI = [
    ("0x0000", "HelloDevice.ino.bootloader.bin"),
    ("0x8000", "HelloDevice.ino.partitions.bin"),
    ("0xe000", "boot_app0.bin"),
    ("0x10000", "HelloDevice.ino.bin"),
    ("0x410000", "tinyuf2.bin"),
]

FLASH_MAP_CELLULAR = [
    ("0x0000", "HelloDevice.ino.bootloader.bin"),
    ("0x8000", "HelloDevice.ino.partitions.bin"),
    ("0xe000", "boot_app0.bin"),
    ("0x10000", "HelloCell.ino.bin"),
    ("0x410000", "tinyuf2.bin"),
]

# === UTILITIES ===
def get_serial_ports_with_names():
    ports = serial.tools.list_ports.comports()
    return [f"{p.device} - {p.description}" for p in ports]

def extract_port_number(combo_value):
    return combo_value.split(" - ")[0].strip()

def touch_reset_serial(port):
    try:
        ser = serial.Serial(port, 1200)
        ser.dtr = False
        ser.close()
    except Exception as e:
        print(f"Touch reset failed: {e}")

# === DOWNLOAD ===
def download_firmware(output_box):
    for filename, url in FIRMWARE_URLS.items():
        try:
            output_box.insert(tk.END, f"📥 Downloading {filename}...\n")
            output_box.see(tk.END)
            urllib.request.urlretrieve(url, filename)
            output_box.insert(tk.END, f"✅ Downloaded {filename}\n")
            output_box.see(tk.END)
        except Exception as e:
            messagebox.showerror("Download Failed", f"Error downloading {filename}:\n{e}")
    output_box.insert(tk.END, "\n")

# === FLASH ===
def flash_firmware(output_box, port_combo, flash_map, label):
    combo_value = port_combo.get().strip()
    if not combo_value:
        messagebox.showerror("No Port Selected", "Please select a COM port before flashing.")
        return

    port = extract_port_number(combo_value)
    output_box.insert(tk.END, f"🔌 Using COM port: {port}\n")
    output_box.insert(tk.END, f"⚡ Flashing {label} firmware...\n\n")
    output_box.see(tk.END)

    missing = [f for _, f in flash_map if not os.path.exists(f)]
    if missing:
        messagebox.showerror("Missing Files", f"Missing required files:\n{', '.join(missing)}")
        return

    touch_reset_serial(port)
    time.sleep(0.5)

    cmd = [
        sys.executable, "-m", "esptool", "--chip", CHIP, "--port", port, "--baud", BAUD,
        "--before", "default_reset", "--after", "hard_reset",
        "write_flash", "-z",
        "--flash_mode", "dio", "--flash_freq", "80m", "--flash_size", "8MB"
    ]

    for addr, fname in flash_map:
        cmd += [addr, fname]

    try:
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            universal_newlines=True,
            bufsize=1
        )

        for line in iter(process.stdout.readline, ''):
            output_box.insert(tk.END, line)
            output_box.see(tk.END)
            output_box.update_idletasks()

        process.stdout.close()
        process.wait()

        if process.returncode == 0:
            messagebox.showinfo("Success", f"✅ {label} firmware flashed to {port}.")
        else:
            messagebox.showerror("Flashing Failed", f"{label} flashing did not complete successfully.")
    except Exception as e:
        messagebox.showerror("Error", str(e))

# === RESCAN ===
def rescan_ports(port_combo):
    port_list = get_serial_ports_with_names()
    port_combo["values"] = port_list
    if port_list:
        port_combo.set(port_list[0])
    else:
        port_combo.set("")

# === GUI ===
def create_gui():
    window = tk.Tk()
    window.title("Flash Hello Firmware")

    large_font = font.Font(size=12)

    # Button Row
    button_frame = tk.Frame(window)
    button_frame.pack(pady=10)

    download_button = tk.Button(button_frame, text="⬇️ Download Firmware", font=large_font, width=20)
    download_button.pack(side=tk.LEFT, padx=10)

    port_label = tk.Label(button_frame, text="Select COM Port:", font=large_font)
    port_label.pack(side=tk.LEFT, padx=5)

    rescan_button = tk.Button(button_frame, text="Rescan Ports", font=large_font)
    rescan_button.pack(side=tk.LEFT, padx=5)

    port_combo = ttk.Combobox(button_frame, width=30, font=large_font)
    rescan_ports(port_combo)
    port_combo.pack(side=tk.LEFT, padx=5)

    # Flash Buttons
    flash_frame = tk.Frame(window)
    flash_frame.pack(pady=5)

    # Use threading for responsive GUI during flashing
    flash_wifi_button = tk.Button(flash_frame, text="📶 Flash WiFi", font=large_font, width=20,
                                  command=lambda: threading.Thread(
                                      target=flash_firmware,
                                      args=(output_box, port_combo, FLASH_MAP_WIFI, "WiFi"),
                                      daemon=True).start())
    flash_wifi_button.pack(side=tk.LEFT, padx=20)

    flash_cell_button = tk.Button(flash_frame, text="📡 Flash Cellular", font=large_font, width=20,
                                   command=lambda: threading.Thread(
                                       target=flash_firmware,
                                       args=(output_box, port_combo, FLASH_MAP_CELLULAR, "Cellular"),
                                       daemon=True).start())
    flash_cell_button.pack(side=tk.LEFT, padx=20)

    clear_button = tk.Button(flash_frame, text="🧹 Clear Log", font=large_font, width=12,
                             command=lambda: output_box.delete("1.0", tk.END))
    clear_button.pack(side=tk.LEFT, padx=5)

    # Output Log
    output_box = scrolledtext.ScrolledText(window, width=100, height=30, font=("Courier", 10))
    output_box.pack(padx=10, pady=10)

    # Assign commands
    download_button.config(command=lambda: download_firmware(output_box))
    rescan_button.config(command=lambda: rescan_ports(port_combo))

    window.mainloop()

if __name__ == "__main__":
    create_gui()