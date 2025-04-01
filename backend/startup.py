#Write a python script which will kill the existing server on 4200 and then run the main.py
import os
import subprocess
import sys
import time
import signal
import platform
import socket
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def is_port_in_use(port: int) -> bool:
    """Check if a port is in use."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        try:
            s.bind(('localhost', port))
            return False
        except OSError:
            return True

def wait_for_port_available(port: int, timeout: int = 30, check_interval: float = 0.5):
    """Wait for a port to become available."""
    start_time = time.time()
    while time.time() - start_time < timeout:
        if not is_port_in_use(port):
            return True
        time.sleep(check_interval)
    return False

def kill_process_on_port(port):
    """Kill process running on specified port."""
    try:
        if platform.system() == "Windows":
            # For Windows
            result = subprocess.run(f"netstat -ano | findstr :{port}", shell=True, capture_output=True, text=True)
            if result.stdout:
                for line in result.stdout.splitlines():
                    if f":{port}" in line:
                        pid = line.strip().split()[-1]
                        logger.info(f"Found process with PID {pid} on port {port}")
                        subprocess.run(f"taskkill /F /PID {pid}", shell=True)
                        logger.info(f"Killed process {pid}")
        else:
            # For Unix-like systems (Linux, macOS)
            result = subprocess.run(["lsof", "-ti", f":{port}"], capture_output=True, text=True)
            if result.stdout:
                pids = result.stdout.strip().split('\n')
                for pid in pids:
                    logger.info(f"Found process with PID {pid} on port {port}")
                    os.kill(int(pid), signal.SIGKILL)
                    logger.info(f"Killed process {pid}")
        
        # Wait for the port to become available
        if not wait_for_port_available(port):
            raise RuntimeError(f"Port {port} is still in use after killing processes")
            
        logger.info(f"Successfully freed port {port}")
    except Exception as e:
        logger.warning(f"Error while killing process on port {port}: {str(e)}")

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
                logger.info(f"{prefix}: {line.strip()}")
                
        import threading
        threading.Thread(target=stream_output, args=(process.stdout, "OUT"), daemon=True).start()
        threading.Thread(target=stream_output, args=(process.stderr, "ERR"), daemon=True).start()
        
        # Wait for server to start
        if not wait_for_port_available(8000, timeout=5):
            time.sleep(2)  # Give the server a bit more time to start
            if process.poll() is None:
                logger.info("Backend server started successfully")
                return process
            else:
                logger.error("Failed to start backend server")
                raise RuntimeError("Backend server failed to start")
                
        return process
    except Exception as e:
        logger.error(f"Error starting backend server: {str(e)}")
        raise

def start_frontend():
    """Start the frontend development server."""
    try:
        # Change to the frontend directory
        frontend_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'frontend')
        os.chdir(frontend_dir)
        
        # Start the frontend server with output streaming
        process = subprocess.Popen(
            ["ng", "serve"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            universal_newlines=True,
            bufsize=1
        )
        
        # Create threads to stream output
        def stream_output(stream, prefix):
            for line in stream:
                logger.info(f"{prefix}: {line.strip()}")
                
        import threading
        threading.Thread(target=stream_output, args=(process.stdout, "FRONTEND OUT"), daemon=True).start()
        threading.Thread(target=stream_output, args=(process.stderr, "FRONTEND ERR"), daemon=True).start()
        
        # Wait for server to start
        if not wait_for_port_available(4200, timeout=5):
            time.sleep(2)  # Give the server a bit more time to start
            if process.poll() is None:
                logger.info("Frontend server started successfully")
                return process
            else:
                logger.error("Failed to start frontend server")
                raise RuntimeError("Frontend server failed to start")
                
        return process
    except Exception as e:
        logger.error(f"Error starting frontend server: {str(e)}")
        raise

if __name__ == "__main__":
    try:
        logger.info("Starting servers...")
        
        # Kill any existing processes on ports 8000 and 4200
        if is_port_in_use(8000):
            logger.info("Port 8000 is in use, killing existing process...")
            kill_process_on_port(8000)
            
        if is_port_in_use(4200):
            logger.info("Port 4200 is in use, killing existing process...")
            kill_process_on_port(4200)
        
        # Start both servers
        backend_process = start_backend()
        frontend_process = start_frontend()
        
        try:
            # Keep the script running and both servers alive
            while True:
                if backend_process.poll() is not None:
                    logger.error("Backend server died unexpectedly")
                    break
                if frontend_process.poll() is not None:
                    logger.error("Frontend server died unexpectedly")
                    break
                time.sleep(1)
        except KeyboardInterrupt:
            logger.info("\nShutting down servers...")
            backend_process.terminate()
            frontend_process.terminate()
            backend_process.wait(timeout=5)
            frontend_process.wait(timeout=5)
            sys.exit(0)
            
    except Exception as e:
        logger.error(f"Fatal error: {str(e)}")
        sys.exit(1)
