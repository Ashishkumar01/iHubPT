#Write a python script which will kill the existing server on 4200 and then run the main.py
import os
import subprocess
import sys
import time
import signal
import platform

def kill_process_on_port(port):
    """Kill process running on specified port."""
    try:
        if platform.system() == "Windows":
            # For Windows
            result = subprocess.run(f"netstat -ano | findstr :{port}", shell=True, capture_output=True, text=True)
            if result.stdout:
                pid = result.stdout.strip().split()[-1]
                subprocess.run(f"taskkill /F /PID {pid}", shell=True)
        else:
            # For Unix-like systems (Linux, macOS)
            result = subprocess.run(["lsof", "-ti", f":{port}"], capture_output=True, text=True)
            if result.stdout:
                pid = result.stdout.strip()
                os.kill(int(pid), signal.SIGKILL)
        print(f"Successfully killed process on port {port}")
    except Exception as e:
        print(f"No process found running on port {port}")

def start_backend():
    """Start the backend server."""
    try:
        # Change to the backend directory
        os.chdir(os.path.dirname(os.path.abspath(__file__)))
        
        # Start the backend server with output streaming
        process = subprocess.Popen(
            [sys.executable, "main.py"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            universal_newlines=True,
            bufsize=1
        )
        
        # Create threads to stream output
        def stream_output(stream, prefix):
            for line in stream:
                print(f"{prefix}: {line}", end='')
                
        import threading
        threading.Thread(target=stream_output, args=(process.stdout, "OUT"), daemon=True).start()
        threading.Thread(target=stream_output, args=(process.stderr, "ERR"), daemon=True).start()
        
        # Wait a bit to check if the process started successfully
        time.sleep(2)
        if process.poll() is None:
            print("Backend server started successfully")
        else:
            print("Failed to start backend server")
            sys.exit(1)
            
        return process
    except Exception as e:
        print(f"Error starting backend server: {e}")
        sys.exit(1)

if __name__ == "__main__":
    # Kill any existing process on port 8000 (backend)
    kill_process_on_port(8000)
    
    # Wait a moment to ensure the port is freed
    time.sleep(1)
    
    # Start the backend server
    backend_process = start_backend()
    
    try:
        # Keep the script running and the backend server alive
        backend_process.wait()
    except KeyboardInterrupt:
        print("\nShutting down servers...")
        backend_process.terminate()
        sys.exit(0)
