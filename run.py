#!/usr/bin/env python3
"""run.py — F5 launcher: codegen → Godot"""
import os
import subprocess
import sys

ROOT  = os.path.dirname(os.path.abspath(__file__))
GODOT = r"D:\Godot\Godot_v4.6.1-stable_win64.exe\Godot_v4.6.1-stable_win64.exe"

subprocess.run([sys.executable, os.path.join(ROOT, "codegen.py")], check=True)
subprocess.Popen([GODOT, "--path", os.path.join(ROOT, "godot")])
