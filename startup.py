import os
import subprocess
import sys
import time
import signal
import platform
import logging
import shutil
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('startup.log')
    ]
)
logger = logging.getLogger(__name__)

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
                        logger.info(f"Successfully killed process with PID {pid}")
        else:
            # For Unix-like systems (Linux, macOS)
            result = subprocess.run(["lsof", "-ti", f":{port}"], capture_output=True, text=True)
            if result.stdout:
                pids = result.stdout.strip().split('\n')
                for pid in pids:
                    logger.info(f"Found process with PID {pid} on port {port}")
                    os.kill(int(pid), signal.SIGKILL)
                    logger.info(f"Successfully killed process with PID {pid}")
        logger.info(f"Successfully killed all processes on port {port}")
    except Exception as e:
        logger.warning(f"No process found running on port {port}: {str(e)}")

def verify_port_available(port, max_attempts=5, delay=1):
    """Verify that a port is available after killing processes."""
    for attempt in range(max_attempts):
        try:
            import socket
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.bind(('localhost', port))
                s.close()
                logger.info(f"Port {port} is available")
                return True
        except OSError:
            logger.warning(f"Port {port} still in use, waiting {delay} seconds...")
            time.sleep(delay)
    return False

def start_backend():
    """Start the backend server."""
    try:
        backend_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "backend")
        logger.info(f"Changing directory to: {backend_dir}")
        os.chdir(backend_dir)
        
        logger.info("Starting backend server...")
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
        threading.Thread(target=stream_output, args=(process.stdout, "BACKEND_OUT"), daemon=True).start()
        threading.Thread(target=stream_output, args=(process.stderr, "BACKEND_ERR"), daemon=True).start()
        
        time.sleep(2)
        if process.poll() is None:
            logger.info("Backend server started successfully")
            return process
        else:
            logger.error("Failed to start backend server")
            raise RuntimeError("Backend server failed to start")
            
    except Exception as e:
        logger.error(f"Error starting backend server: {str(e)}")
        raise

def start_frontend():
    """Start the frontend development server."""
    try:
        clear_angular_cache()
        logger.info("Starting frontend server...")
        frontend_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "frontend")
        
        # Install dependencies if needed
        if not os.path.exists(os.path.join(frontend_dir, "node_modules")):
            logger.info("Installing frontend dependencies...")
            subprocess.run(["npm", "install"], cwd=frontend_dir, check=True)
        
        # Start the frontend server
        frontend_process = subprocess.Popen(
            ["npm", "start"],
            cwd=frontend_dir,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        # Wait for the server to start
        time.sleep(2)
        
        if frontend_process.poll() is not None:
            stdout, stderr = frontend_process.communicate()
            logger.error(f"Frontend server failed to start:\nstdout: {stdout}\nstderr: {stderr}")
            raise Exception("Frontend server failed to start")
        
        logger.info("Frontend server started successfully")
        return frontend_process
        
    except Exception as e:
        logger.error(f"Error starting frontend server: {str(e)}")
        raise

def monitor_servers(backend_process, frontend_process):
    """Monitor server processes and restart them if they crash."""
    while True:
        try:
            # Check backend status
            if backend_process.poll() is not None:
                logger.error("Backend server stopped unexpectedly, attempting restart...")
                kill_process_on_port(8000)
                if verify_port_available(8000):
                    backend_process = start_backend()
                else:
                    raise RuntimeError("Failed to free backend port")

            # Check frontend status
            if frontend_process.poll() is not None:
                logger.error("Frontend server stopped unexpectedly, attempting restart...")
                kill_process_on_port(4200)
                if verify_port_available(4200):
                    frontend_process = start_frontend()
                else:
                    raise RuntimeError("Failed to free frontend port")

            time.sleep(5)
        except KeyboardInterrupt:
            raise
        except Exception as e:
            logger.error(f"Error in server monitoring: {str(e)}")
            raise

def clear_angular_cache():
    """Clear the Angular cache directory."""
    try:
        frontend_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "frontend")
        cache_dir = os.path.join(frontend_dir, ".angular")
        
        if os.path.exists(cache_dir):
            logger.info("Clearing Angular cache...")
            shutil.rmtree(cache_dir)
            logger.info("Angular cache cleared successfully")
        else:
            logger.info("No Angular cache found")
    except Exception as e:
        logger.error(f"Error clearing Angular cache: {str(e)}")
        raise

if __name__ == "__main__":
    try:
        logger.info("=== Starting Application Servers ===")
        
        # Kill existing processes
        logger.info("Killing existing processes...")
        kill_process_on_port(8000)  # Backend
        kill_process_on_port(4200)  # Frontend
        
        # Verify ports are available
        if not verify_port_available(8000) or not verify_port_available(4200):
            logger.error("Failed to free required ports")
            sys.exit(1)
        
        # Start both servers
        backend_process = start_backend()
        frontend_process = start_frontend()
        
        logger.info("Both servers started successfully")
        
        # Monitor and keep servers alive
        monitor_servers(backend_process, frontend_process)
        
    except KeyboardInterrupt:
        logger.info("\nShutting down servers gracefully...")
        if 'backend_process' in locals():
            backend_process.terminate()
            backend_process.wait(timeout=5)
        if 'frontend_process' in locals():
            frontend_process.terminate()
            frontend_process.wait(timeout=5)
        logger.info("Servers shut down successfully")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Fatal error: {str(e)}")
        # Attempt to clean up
        if 'backend_process' in locals():
            backend_process.terminate()
        if 'frontend_process' in locals():
            frontend_process.terminate()
        sys.exit(1) 