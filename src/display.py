import subprocess
import os
import logging

def display_image(image_path):
    subprocess.run(
        ['sudo', 'killall', '-q', 'fbi'],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    )
    fbi_cmd = [
        "sudo", "fbi",
        "-T", "1",
        "-d", "/dev/fb0",
        "-a",
        "-noverbose",
        "-nocomments",
        str(image_path)
    ]
    with open(os.devnull, 'w') as devnull:
        subprocess.run(fbi_cmd, check=True, stdout=devnull, stderr=devnull)

def cleanup():
    subprocess.run(
        ['sudo', 'killall', '-q', 'fbi'],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    )
    logging.info("Cleaned up fbi process.")

