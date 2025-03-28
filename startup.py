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
        backend_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "backend")
        os.chdir(backend_dir)
        
        process = subprocess.Popen(
            [sys.executable, "main.py"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            universal_newlines=True
        )
        
        time.sleep(2)
        if process.poll() is None:
            print("Backend server started successfully")
        else:
            stdout, stderr = process.communicate()
            print("Failed to start backend server")
            print("Error:", stderr)
            sys.exit(1)
            
        return process
    except Exception as e:
        print(f"Error starting backend server: {e}")
        sys.exit(1)

def start_frontend():
    """Start the frontend development server."""
    try:
        frontend_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "frontend")
        os.chdir(frontend_dir)
        
        process = subprocess.Popen(
            ["ng", "serve"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            universal_newlines=True
        )
        
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
    # Kill existing processes
    kill_process_on_port(8000)  # Backend
    kill_process_on_port(4200)  # Frontend
    
    # Wait a moment to ensure ports are freed
    time.sleep(1)
    
    # Start both servers
    print("\nStarting backend server...")
    backend_process = start_backend()
    
    print("\nStarting frontend server...")
    frontend_process = start_frontend()
    
    try:
        # Keep the script running and both servers alive
        while True:
            if backend_process.poll() is not None:
                print("Backend server stopped unexpectedly")
                frontend_process.terminate()
                sys.exit(1)
            if frontend_process.poll() is not None:
                print("Frontend server stopped unexpectedly")
                backend_process.terminate()
                sys.exit(1)
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nShutting down servers...")
        backend_process.terminate()
        frontend_process.terminate()
        sys.exit(0) 