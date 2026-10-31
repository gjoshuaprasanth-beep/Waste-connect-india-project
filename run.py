"""
WasteConnect India - Application Launcher
Runs local server on http://localhost:8080
"""

import sys
import os
import webbrowser
from server import run_server, PORT

def main():
    print("================================================================")
    print(" WasteConnect India - B2B Healthcare & Industrial Waste Platform")
    print(" Bio-Medical Waste (2016) & Hazardous Waste Rules (2016)")
    print(f" URL: http://localhost:{PORT}")
    print(" Press Ctrl+C to terminate.")
    print("================================================================")
    run_server(PORT)

if __name__ == "__main__":
    main()
