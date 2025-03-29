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

def start_frontend():
    """Start the frontend development server."""
    try:
        # Change to the frontend directory
        os.chdir(os.path.dirname(os.path.abspath(__file__)))
        
        # Start the frontend server using ng serve
        process = subprocess.Popen(
            ["ng", "serve"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            universal_newlines=True
        )
        
        # Wait a bit to check if the process started successfully
        time.sleep(5)
        if process.poll() is None:
            print("Frontend server started successfully")
        else:
            stdout, stderr = process.communicate()
            print("Failed to start frontend server")
            print("Error:", stderr)
            sys.exit(1)
            
        return process
    except Exception as e:
        print(f"Error starting frontend server: {e}")
        sys.exit(1)

if __name__ == "__main__":
    # Kill any existing process on port 4200 (frontend)
    kill_process_on_port(4200)
    
    # Wait a moment to ensure the port is freed
    time.sleep(1)
    
    # Start the frontend server
    frontend_process = start_frontend()
    
    try:
        # Keep the script running and the frontend server alive
        frontend_process.wait()
    except KeyboardInterrupt:
        print("\nShutting down servers...")
        frontend_process.terminate()
        sys.exit(0) 