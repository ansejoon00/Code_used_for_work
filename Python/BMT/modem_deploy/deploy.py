#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Modem IP File Deployment Script

Deploys file to multiple IP via SFTP with infinite retry mechanism.

Workflow:
1. Read IP list from ip.txt
2. Remove SSH host keys for all IP
3. For each IP (parallel processing):
   a. Ping until success (infinite retry)
   b. SSH connection attempts (ssh_attempts_per_round times)
   c. If SSH fails, retry from ping
   d. Transfer all file (each file retries until success)
   e. Move mode: mv .BMT to original + kill processes (retries until success)
   f. Nomove mode: just transfer file with .BMT extension
4. Retry failed IP until all succeed
5. Send notifications and print statistics

Features:
- Infinite retry for all operations until success
- Multiple SFTP methods: pexpect -> paramiko -> subprocess (fallback)
- Thread-safe logging
- Progress tracking and statistics
- Email notifications
- File verification (size/hash check)
"""

import os
import sys
import time
import subprocess
import hashlib
import logging
import json
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Lock
from typing import Dict, List, Optional, Set, Any
from contextlib import contextmanager

# ============================================================================
# Imports
# ============================================================================

try:
    import paramiko
    HAS_PARAMIKO = True
except ImportError:
    HAS_PARAMIKO = False
    print("Warning: paramiko not found. Trying alternative method...")

try:
    import pexpect
    HAS_PEXPECT = True
except ImportError:
    HAS_PEXPECT = False

# ============================================================================
# Configuration Constants
# ============================================================================

CONFIG_DIR = "config"
IP_TXT = os.path.join(CONFIG_DIR, "ip.txt")
FILE_TXT = os.path.join(CONFIG_DIR, "file.txt")
FILE_DIR = "file"
COMPLETE_TXT = "complete.txt"
CONFIG_JSON = os.path.join(CONFIG_DIR, "config.json")

# ============================================================================
# Classes
# ============================================================================

class DeploymentStats:
    """Statistics tracker for deployment process."""
    
    def __init__(self):
        self.start_time: Optional[float] = None
        self.end_time: Optional[float] = None
        self.total_ip: int = 0
        self.success_ip: int = 0
        self.fail_ip: int = 0
        self.ip_time: Dict[str, int] = {}
    
    def record_reset(self) -> None:
        """Reset all statistics."""
        self.start_time = time.time()
        self.end_time = None
        self.total_ip = 0
        self.success_ip = 0
        self.fail_ip = 0
        self.ip_time = {}
    
    def record_success(self, ip: str, elapsed: int) -> None:
        """Record successful deployment for an IP."""
        self.success_ip += 1
        self.ip_time[ip] = elapsed
        self.fail_ip = self.total_ip - self.success_ip
    
    def record_fail(self) -> None:
        """Update failure count."""
        self.fail_ip = self.total_ip - self.success_ip


class Logger:
    """Thread-safe logger for console and file output."""
    
    def __init__(self):
        self.log_file: Optional[Any] = None
        self.log_file_path: Optional[str] = None
        self.print_lock = Lock()
        self.last_progress_log_time = 0.0
        self.progress_log_interval = 5
        self.progress_log_lock = Lock()
        self.status_map = {
            'RUNNING': '▶',
            'SUCCESS': '✓',
            'FAILED': '✗',
            'WARNING': '⚠',
            'INFO': '>>'
        }
    
    def init_log_file(self, log_dir: str = "log") -> None:
        """Initialize log file with timestamp."""
        if not os.path.exists(log_dir):
            try:
                os.makedirs(log_dir)
            except OSError as e:
                self.log_message(f"Log dir creation failed : {e}", status='WARNING')
        
        log_timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.log_file_path = os.path.join(log_dir, f"deploy_{log_timestamp}.log")
        try:
            self.log_file = open(self.log_file_path, 'w', encoding='utf-8')
            self.log_message(f"Log file : {self.log_file_path}", status='INFO')
        except (OSError, IOError) as e:
            self.log_file = None
            self.log_message(f"Log creation failed : {e}", status='WARNING')
    
    def close(self) -> None:
        """Close log file."""
        if self.log_file:
            try:
                log_path = self.log_file_path
                self.log_file.close()
                self.log_file = None
                if log_path:
                    # Use print instead of log_message to avoid writing to closed file
                    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [>>] Log saved : {log_path}")
            except (OSError, IOError, ValueError):
                pass
    
    def log_message(self, message: str, ip: Optional[str] = None, status: Optional[str] = None) -> None:
        """Thread-safe logging to console and file."""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        status_icon = self.status_map.get(status, '') if status else ""
        status_prefix = f"{status_icon} " if status_icon else ""
        
        if ip:
            log_line = f"[{timestamp}] [{ip}] {status_prefix}{message}\n"
            console_line = f"[{timestamp}] [{ip}] {status_prefix}{message}"
        else:
            log_line = f"[{timestamp}] {status_prefix}{message}\n"
            console_line = f"[{timestamp}] {status_prefix}{message}"
        
        with self.print_lock:
            print(console_line)
            if self.log_file:
                try:
                    self.log_file.write(log_line)
                    self.log_file.flush()
                except (OSError, IOError):
                    pass
    
    def log_progress(self, stats: DeploymentStats) -> None:
        """Log progress with throttling."""
        current_time = time.time()
        success_count = stats.success_ip
        total_count = stats.total_ip
        
        if total_count > 0:
            with self.progress_log_lock:
                if current_time - self.last_progress_log_time >= self.progress_log_interval:
                    self.last_progress_log_time = current_time
                    time.sleep(0.05)
                    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    progress_line = f"[{timestamp}] [>>] Progress : {success_count} / {total_count}\n"
                    with self.print_lock:
                        print(f"[{timestamp}] [>>] Progress : {success_count} / {total_count}")
                        if self.log_file:
                            try:
                                self.log_file.write(progress_line)
                                self.log_file.flush()
                            except (OSError, IOError):
                                pass


# Global logger instance
logger = Logger()

# ============================================================================
# Network Functions
# ============================================================================

def format_ip_for_sftp(ip: str) -> str:
    """Format IP address for SFTP (handle IPv6 brackets)."""
    if ":" in ip and not ip.startswith("["):
        return f"[{ip}]"
    return ip


def ping_check(ip: str, config: Dict[str, Any]) -> bool:
    """Check host reachability via ping (IPv4/IPv6, Windows/Linux)."""
    ping_timeout = config['ping']['timeout']
    try:
        if sys.platform == "win32":
            result = subprocess.run(
                ["ping", "-n", "1", "-w", str(ping_timeout * 1000), ip],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=ping_timeout + 1
            )
        else:
            result = subprocess.run(
                ["ping", "-c", "1", "-W", str(ping_timeout), ip],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=ping_timeout + 1
            )
        return result.returncode == 0
    except (subprocess.TimeoutExpired, OSError, ValueError) as e:
        logger.log_message(f"Ping error : {type(e).__name__}", ip, 'WARNING')
        return False


def wait_for_ping(ip: str, config: Dict[str, Any], stats: DeploymentStats) -> bool:
    """Wait for connectivity (infinite retry until success)."""
    logger.log_message("Waiting ping...", ip, 'RUNNING')
    
    attempt = 0
    start_time = time.time()
    ping_interval = config['ping']['interval']
    
    while True:
        attempt += 1
        if ping_check(ip, config):
            logger.log_message(f"Ping OK ({attempt})", ip, 'SUCCESS')
            return True
        
        if attempt % 10 == 0:
            elapsed = int(time.time() - start_time)
            logger.log_message(f"Retry ping ({attempt}, {elapsed}s)", ip, 'RUNNING')
            logger.log_progress(stats)
        
        time.sleep(ping_interval)


@contextmanager
def ssh_connection(ip: str, config: Dict[str, Any], timeout: int = 10):
    """Context manager for SSH connection."""
    ssh = None
    try:
        if not HAS_PARAMIKO:
            raise RuntimeError("paramiko not available")
        
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(
            ip,
            port=config['ssh']['port'],
            username=config['ssh']['user'],
            password=config['ssh']['password'],
            timeout=timeout,
            key_filename=None,
            allow_agent=False,
            look_for_keys=False
        )
        yield ssh
    except (paramiko.AuthenticationException, paramiko.SSHException, 
            paramiko.BadHostKeyException, OSError) as e:
        logger.log_message(f"SSH connection error : {type(e).__name__}", ip, 'WARNING')
        raise
    finally:
        if ssh:
            try:
                ssh.close()
            except Exception:
                pass


def wait_for_ssh_ready(ip: str, config: Dict[str, Any], stats: DeploymentStats) -> bool:
    """
    Wait for SSH ready with ping fallback.
    Retries: ping (until success) -> SSH (ssh_attempts_per_round times) -> repeat.
    Returns True when SSH is ready, False only if paramiko is not available.
    """
    ssh_attempts_per_round = config['retry']['ssh_attempts_per_round']
    ssh_attempt_interval = config['retry']['ssh_attempt_interval']
    
    if not HAS_PARAMIKO:
        # Without paramiko, just wait for ping
        wait_for_ping(ip, config, stats)
        return True
    
    paramiko_logger = logging.getLogger("paramiko")
    original_level = paramiko_logger.level
    paramiko_logger.setLevel(logging.CRITICAL)
    
    try:
        while True:
            wait_for_ping(ip, config, stats)
            
            logger.log_message("Waiting SSH...", ip, 'RUNNING')
            
            for ssh_try_count in range(1, ssh_attempts_per_round + 1):
                try:
                    with ssh_connection(ip, config, timeout=5) as ssh:
                        stdin, stdout, stderr = ssh.exec_command("echo test", timeout=3)
                        exit_status = stdout.channel.recv_exit_status()
                        
                        if exit_status == 0:
                            logger.log_message(f"SSH OK ({ssh_try_count})", ip, 'SUCCESS')
                            return True
                except Exception:
                    if ssh_try_count % 5 == 0:
                        logger.log_message(
                            f"Retry SSH ({ssh_try_count}/{ssh_attempts_per_round})", 
                            ip, 'RUNNING'
                        )
                
                time.sleep(ssh_attempt_interval)
            
            logger.log_message(
                f"SSH failed ({ssh_attempts_per_round}), retry ping...", 
                ip, 'RUNNING'
            )
    finally:
        paramiko_logger.setLevel(original_level)

# ============================================================================
# File Transfer
# ============================================================================

def check_remote_directory(sftp: Any, remote_file_path: str) -> None:
    """Check and create remote directory if needed."""
    remote_dir = os.path.dirname(remote_file_path)
    if not remote_dir:
        return
    
    try:
        if not remote_dir.startswith('/'):
            remote_dir = '/' + remote_dir
        dirs = [d for d in remote_dir.split('/') if d]
        current_path = ''
        
        for d in dirs:
            current_path = current_path + '/' + d if current_path else '/' + d
            try:
                sftp.mkdir(current_path)
            except (IOError, OSError):
                # Directory might already exist, verify
                try:
                    sftp.stat(current_path)
                except (IOError, OSError):
                    pass
    except Exception:
        pass


@contextmanager
def sftp_connection(ip: str, config: Dict[str, Any]):
    """Context manager for SFTP connection."""
    transport = None
    sftp = None
    try:
        if not HAS_PARAMIKO:
            raise RuntimeError("paramiko not available")
        
        transport = paramiko.Transport((ip, config['ssh']['port']))
        transport.connect(
            username=config['ssh']['user'], 
            password=config['ssh']['password']
        )
        sftp = paramiko.SFTPClient.from_transport(transport)
        yield sftp
    except (paramiko.AuthenticationException, paramiko.SSHException, 
            paramiko.BadHostKeyException, OSError) as e:
        logger.log_message(f"SFTP connection error : {type(e).__name__}", ip, 'WARNING')
        raise
    finally:
        if sftp:
            try:
                sftp.close()
            except Exception:
                pass
        if transport:
            try:
                transport.close()
            except Exception:
                pass


def send_file_sftp_paramiko(ip: str, local_file_path: str, remote_file_path: str, 
                            config: Dict[str, Any]) -> bool:
    """Send file via SFTP (paramiko). Creates dirs, verifies size."""
    try:
        with sftp_connection(ip, config) as sftp:
            check_remote_directory(sftp, remote_file_path)
            sftp.put(local_file_path, remote_file_path)
            
            # Verify file size
            try:
                remote_stat = sftp.stat(remote_file_path)
                local_stat = os.stat(local_file_path)
                if remote_stat.st_size == local_stat.st_size:
                    logger.log_message(f"Sent {os.path.basename(local_file_path)}", ip, 'SUCCESS')
                    return True
                else:
                    logger.log_message("Size mismatch", ip, 'FAILED')
                    return False
            except (IOError, OSError) as e:
                logger.log_message(f"File verification error : {type(e).__name__}", ip, 'WARNING')
                return False
    except Exception as e:
        logger.log_message(f"Transfer error : {type(e).__name__}", ip, 'WARNING')
        return False


def send_file_sftp_pexpect(ip: str, local_file_path: str, remote_file_path: str, 
                          config: Dict[str, Any]) -> bool:
    """Send file via SFTP (pexpect). Auto password, verifies hash."""
    if not HAS_PEXPECT:
        return False
    
    sftp_ip = format_ip_for_sftp(ip)
    sftp_cmd = (
        f"sftp -P {config['ssh']['port']} "
        f"-o HostKeyAlgorithms=ssh-rsa "
        f"-o StrictHostKeyChecking=no "
        f"-o ConnectTimeout=10 "
        f"{config['ssh']['user']}@{sftp_ip}"
    )
    
    try:
        child = pexpect.spawn(sftp_cmd, timeout=30, encoding='utf-8')
        
        index = child.expect(['password:', 'Password:', pexpect.EOF, pexpect.TIMEOUT], timeout=10)
        
        if index < 2:
            child.sendline(config['ssh']['password'])
            child.expect(['sftp>', pexpect.EOF, pexpect.TIMEOUT], timeout=10)
        
        child.sendline(f"rm {remote_file_path}")
        child.expect(['sftp>', pexpect.EOF, pexpect.TIMEOUT], timeout=10)
        
        child.sendline(f"put {local_file_path} {remote_file_path}")
        child.expect(['sftp>', pexpect.EOF, pexpect.TIMEOUT], timeout=30)
        
        child.sendline("quit")
        child.expect(pexpect.EOF, timeout=5)
        child.close()
        
        if child.exitstatus == 0:
            local_hash = get_file_hash(local_file_path)
            if local_hash and HAS_PARAMIKO:
                time.sleep(1)
                remote_hash = get_remote_file_hash(ip, remote_file_path, config)
                if remote_hash:
                    if local_hash == remote_hash:
                        logger.log_message(f"Sent {os.path.basename(local_file_path)}", ip, 'SUCCESS')
                        return True
                    else:
                        logger.log_message("Hash mismatch", ip, 'FAILED')
                        return False
                else:
                    logger.log_message(f"Sent {os.path.basename(local_file_path)}", ip, 'SUCCESS')
                    return True
            else:
                logger.log_message(f"Sent {os.path.basename(local_file_path)}", ip, 'SUCCESS')
                return True
        else:
            return False
    except (pexpect.ExceptionPexpect, OSError, ValueError) as e:
        logger.log_message(f"Pexpect error : {type(e).__name__}", ip, 'WARNING')
        return False


def send_file_sftp_subprocess(ip: str, local_file_path: str, remote_file_path: str, 
                              config: Dict[str, Any]) -> bool:
    """Send file via SFTP (subprocess fallback)."""
    sftp_ip = format_ip_for_sftp(ip)
    sftp_commands = f"put {local_file_path} {remote_file_path}\nquit\n"
    
    try:
        result = subprocess.run(
            [
                "sftp",
                "-P", str(config['ssh']['port']),
                "-o", "HostKeyAlgorithms ssh-rsa",
                "-o", "StrictHostKeyChecking=no",
                "-o", "ConnectTimeout=10",
                f"{config['ssh']['user']}@{sftp_ip}"
            ],
            input=sftp_commands,
            text=True,
            timeout=30,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        
        if result.returncode == 0:
            logger.log_message(f"Sent {os.path.basename(local_file_path)}", ip, 'SUCCESS')
            return True
        else:
            return False
    except (subprocess.TimeoutExpired, OSError, ValueError) as e:
        logger.log_message(f"Subprocess error : {type(e).__name__}", ip, 'WARNING')
        return False


def send_file_with_fallback(ip: str, local_file_path: str, remote_file_path: str, 
                           config: Dict[str, Any]) -> bool:
    """Send file using available methods with fallback."""
    # Try pexpect first
    if HAS_PEXPECT:
        if send_file_sftp_pexpect(ip, local_file_path, remote_file_path, config):
            return True
    
    # Try paramiko
    if HAS_PARAMIKO:
        if send_file_sftp_paramiko(ip, local_file_path, remote_file_path, config):
            return True
    
    # Fallback to subprocess
    return send_file_sftp_subprocess(ip, local_file_path, remote_file_path, config)

# ============================================================================
# File Verification
# ============================================================================

def get_file_hash(file_path: str) -> Optional[str]:
    """Calculate SHA256 hash. Returns hex string or None."""
    sha256_hash = hashlib.sha256()
    try:
        with open(file_path, "rb") as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        return sha256_hash.hexdigest()
    except (OSError, IOError) as e:
        logger.log_message(f"Hash calculation error : {type(e).__name__}", status='WARNING')
        return None


def get_remote_file_hash(ip: str, remote_file_path: str, config: Dict[str, Any]) -> Optional[str]:
    """Get remote file SHA256 hash via SSH. Returns hex string or None."""
    try:
        with ssh_connection(ip, config, timeout=10) as ssh:
            stdin, stdout, stderr = ssh.exec_command(f"sha256sum {remote_file_path}")
            output = stdout.read().decode().strip()
            
            if output:
                hash_value = output.split()[0]
                return hash_value
            return None
    except Exception as e:
        logger.log_message(f"Remote hash error : {type(e).__name__}", ip, 'WARNING')
        return None

# ============================================================================
# Remote Commands
# ============================================================================

def execute_remote_commands(ip: str, remote_file_path: str, filename: str, 
                            config: Dict[str, Any]) -> bool:
    """Execute remote: mv .BMT to original, kill matching processes."""
    try:
        with ssh_connection(ip, config, timeout=10) as ssh:
            # Move .BMT file to original
            remote_file_original = remote_file_path.replace('.BMT', '')
            mv_command = f"mv {remote_file_path} {remote_file_original}"
            stdin, stdout, stderr = ssh.exec_command(mv_command)
            exit_status = stdout.channel.recv_exit_status()
            
            if exit_status != 0:
                error = stderr.read().decode().strip()
                logger.log_message(f"Move failed : {error}", ip, 'FAILED')
                return False
            
            # Kill matching processes
            ps_command = f"ps | grep {filename} | grep -v grep | awk '{{print $1}}'"
            stdin, stdout, stderr = ssh.exec_command(ps_command)
            pids = stdout.read().decode().strip()
            
            if pids:
                for pid in pids.split('\n'):
                    pid = pid.strip()
                    if pid and pid.isdigit():
                        try:
                            kill_stdin, kill_stdout, kill_stderr = ssh.exec_command(f"kill -9 {pid}")
                            exit_status = kill_stdout.channel.recv_exit_status()
                            if exit_status == 0:
                                logger.log_message(f"Process {pid} terminated", ip, 'SUCCESS')
                        except Exception:
                            pass
            
            return True
    except Exception as e:
        logger.log_message(f"Remote command error : {type(e).__name__}", ip, 'WARNING')
        return False

# ============================================================================
# Notification Functions
# ============================================================================

def send_email_notification(config: Dict[str, Any], subject: str, message: str) -> bool:
    """Send email via SMTP. Returns True if successful."""
    if not config.get('notification', {}).get('email', {}).get('enabled', False):
        return False
    
    email_config = config['notification']['email']
    
    try:
        import smtplib
        from email.mime.text import MIMEText
        from email.mime.multipart import MIMEMultipart
        
        smtp_server = email_config.get('smtp_server', 'smtp.gmail.com')
        smtp_port = email_config.get('smtp_port', 587)
        sender_email = email_config.get('sender_email', '')
        sender_password = email_config.get('sender_password', '')
        recipient_emails = email_config.get('recipient_emails', [])
        
        if not sender_email or not recipient_emails:
            return False
        
        msg = MIMEMultipart()
        msg['From'] = sender_email
        msg['To'] = ', '.join(recipient_emails)
        msg['Subject'] = subject
        
        msg.attach(MIMEText(message, 'plain', 'utf-8'))
        
        server = smtplib.SMTP(smtp_server, smtp_port)
        server.starttls()
        server.login(sender_email, sender_password)
        server.send_message(msg)
        server.quit()
        
        recipient_list = ', '.join(recipient_emails)
        logger.log_message(f"Email sent to : {recipient_list}", status='INFO')
        return True
    except (smtplib.SMTPException, OSError, ValueError) as e:
        logger.log_message(f"Email failed : {type(e).__name__}", status='WARNING')
        return False


def send_notification(config: Dict[str, Any], subject: str, message: str, 
                      notify_on: Optional[List[str]] = None) -> None:
    """Send email notification based on config."""
    notification_config = config.get('notification', {})
    if not notification_config.get('enabled', False):
        return
    
    # Send email notification
    if notification_config.get('email', {}).get('enabled', False):
        send_email_notification(config, subject, message)

# ============================================================================
# Configuration
# ============================================================================

def load_config() -> Dict[str, Any]:
    """Load config.json, create default if missing. Returns config dict."""
    default_config = {
        "ssh": {
            "port": 22,
            "user": "root",
            "password": ""
        },
        "ping": {
            "interval": 5,
            "timeout": 2
        },
        "retry": {
            "interval": 10,
            "ssh_attempts_per_round": 10,
            "ssh_attempt_interval": 3
        },
        "notification": {
            "enabled": True,
            "notify_on": ["start", "ip_success", "complete"],
            "email": {
                "enabled": True,
                "smtp_server": "smtp.gmail.com",
                "smtp_port": 587,
                "sender_email": "asj87451107@gmail.com",
                "sender_password": "",
                "recipient_emails": ["sjan@gaias.co.kr"]
            }
        }
    }
    
    if not os.path.exists(CONFIG_JSON):
        try:
            with open(CONFIG_JSON, 'w', encoding='utf-8') as f:
                json.dump(default_config, f, indent=4)
            logger.log_message(f"Created default config : {CONFIG_JSON}", status='INFO')
        except (OSError, IOError) as e:
            logger.log_message(f"Config creation error : {type(e).__name__}", status='WARNING')
        return default_config
    
    try:
        with open(CONFIG_JSON, 'r', encoding='utf-8') as f:
            config = json.load(f)
        
        merged_config = default_config.copy()
        for key in merged_config:
            if key in config:
                if isinstance(merged_config[key], dict) and isinstance(config[key], dict):
                    merged_config[key].update(config[key])
                else:
                    merged_config[key] = config[key]
        
        return merged_config
    except (OSError, IOError, json.JSONDecodeError) as e:
        logger.log_message(f"Error loading {CONFIG_JSON}, using defaults : {type(e).__name__} : {e}", status='WARNING')
        return default_config

# ============================================================================
# File I/O
# ============================================================================

def init_complete_file() -> None:
    """Clear complete.txt at start."""
    try:
        if os.path.exists(COMPLETE_TXT):
            os.remove(COMPLETE_TXT)
    except OSError:
        pass


def record_complete_ip(ip: str) -> None:
    """Write successful IP to complete.txt (no duplicates)."""
    try:
        existing_ips: Set[str] = set()
        if os.path.exists(COMPLETE_TXT):
            with open(COMPLETE_TXT, 'r', encoding='utf-8') as f:
                existing_ips = set(line.strip() for line in f if line.strip())
        
        if ip not in existing_ips:
            with open(COMPLETE_TXT, 'a', encoding='utf-8') as f:
                f.write(f"{ip}\n")
    except (OSError, IOError):
        pass


def read_ip_list(ip_file: str) -> List[str]:
    """Read IP list from file (ignores empty lines and # comments)."""
    ip_list = []
    if not os.path.exists(ip_file):
        logger.log_message(f"Error : {ip_file} not found", status='FAILED')
        return ip_list
    
    try:
        with open(ip_file, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#'):
                    ip_list.append(line)
    except (OSError, IOError) as e:
        logger.log_message(f"Error reading {ip_file} : {type(e).__name__}", status='FAILED')
    
    return ip_list


def read_file(file_map: str) -> Dict[str, str]:
    """Read file mapping (filename=path, default path if no '=')."""
    file_map_dict: Dict[str, str] = {}
    if not os.path.exists(file_map):
        logger.log_message(f"Error : {file_map} not found", status='FAILED')
        return file_map_dict
    
    try:
        with open(file_map, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                
                if '=' in line:
                    filename, path = line.split('=', 1)
                    filename = filename.strip()
                    path = path.strip()
                else:
                    filename = line
                    path = "/usr/local/bin/"
                
                if path and not path.endswith('/'):
                    path = path + '/'
                
                file_map_dict[filename] = path
    except (OSError, IOError) as e:
        logger.log_message(f"Error reading {file_map} : {type(e).__name__}", status='FAILED')
    
    return file_map_dict


def remove_host_key(ip: str, config: Dict[str, Any]) -> None:
    """Remove host key from known_hosts to avoid SSH key mismatch errors."""
    host_key = format_ip_for_sftp(ip)
    host_key = f"{host_key}:{config['ssh']['port']}"
    
    known_hosts_file = os.path.expanduser("~/.ssh/known_hosts")
    
    if not os.path.exists(known_hosts_file):
        return
    
    try:
        result = subprocess.run(
            [
                "ssh-keygen",
                "-f", known_hosts_file,
                "-R", host_key
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=5
        )
        # Note: We don't check the result as "not found" is also acceptable
    except (subprocess.TimeoutExpired, OSError, ValueError):
        pass

# ============================================================================
# Main Processing
# ============================================================================

def make_remote_file_path(remote_path: str, filename: str) -> str:
    """Build remote file path with .BMT extension."""
    if remote_path.endswith('/'):
        return remote_path + filename + '.BMT'
    else:
        return remote_path + '/' + filename + '.BMT'


def send_single_file(ip: str, filename: str, local_file_path: str, remote_file_path: str, 
                    move_mode: bool, config: Dict[str, Any]) -> bool:
    """Send single file with infinite retry until success."""
    send_try_count = 0
    
    while True:
        send_try_count += 1
        if send_try_count == 1:
            logger.log_message(f"Sending {filename}...", ip, 'RUNNING')
        else:
            logger.log_message(f"Retry {filename} ({send_try_count})", ip, 'RUNNING')
        
        success = send_file_with_fallback(ip, local_file_path, remote_file_path, config)
        
        if success:
            if move_mode and HAS_PARAMIKO:
                if execute_remote_commands(ip, remote_file_path, filename, config):
                    logger.log_message(f"Completed {filename}", ip, 'SUCCESS')
                    return True
                else:
                    time.sleep(2)
                    continue
            else:
                if move_mode:
                    logger.log_message(f"Sent {filename} (move skipped)", ip, 'SUCCESS')
                else:
                    logger.log_message(f"Sent {filename} (.BMT)", ip, 'SUCCESS')
                return True
        else:
            time.sleep(5)


def process_single_ip(ip: str, file_map: Dict[str, str], move_mode: bool, 
                      config: Dict[str, Any], stats: DeploymentStats) -> bool:
    """Process IP: connect → upload → deploy (infinite retry until success)."""
    try:
        logger.log_message(f"Processing {ip}", ip, 'RUNNING')
        
        ip_start_time = time.time()
        wait_for_ssh_ready(ip, config, stats)
        
        for filename, remote_path in file_map.items():
            local_file_path = os.path.join(FILE_DIR, filename)
            
            if not os.path.exists(local_file_path):
                logger.log_message(f"File not found : {filename}", ip, 'WARNING')
                continue
            
            remote_file_path = make_remote_file_path(remote_path, filename)
            send_single_file(ip, filename, local_file_path, remote_file_path, move_mode, config)
        
        ip_elapsed = int(time.time() - ip_start_time)
        stats.record_success(ip, ip_elapsed)
        logger.log_message("Deploy complete", ip, 'SUCCESS')
        return True
    except Exception as e:
        logger.log_message(f"Error : {type(e).__name__}", ip, 'FAILED')
        stats.record_fail()
        return False


def print_statistics(stats: DeploymentStats) -> None:
    """Print deployment summary."""
    if not stats.start_time:
        return
    
    total_time = int(stats.end_time - stats.start_time) if stats.end_time else int(time.time() - stats.start_time)
    success_count = stats.success_ip
    fail_count = stats.fail_ip
    total = stats.total_ip
    success_rate = int(success_count*100/total) if total > 0 else 0
    
    logger.log_message("=" * 60, status='INFO')
    logger.log_message("Summary", status='INFO')
    logger.log_message("=" * 60, status='INFO')
    logger.log_message(f"Total IP : {total}", status='INFO')
    logger.log_message(f"Successful : {success_count} ({success_rate}%)", status='INFO')
    logger.log_message(f"Failed : {fail_count} ({int(fail_count*100/total) if total > 0 else 0}%)", status='INFO')
    logger.log_message(f"Time : {total_time}s", status='INFO')
    
    if stats.ip_time:
        times = list(stats.ip_time.values())
        if times:
            avg_time = int(sum(times) / len(times))
            min_time = min(times)
            max_time = max(times)
            logger.log_message(f"Avg : {avg_time}s, Min : {min_time}s, Max : {max_time}s", status='INFO')
    
    logger.log_message("=" * 60, status='INFO')


def get_mode_input() -> bool:
    """Get deployment mode from user input."""
    while True:
        mode_input = input("Enter mode (move/nomove) : ").strip().lower()
        if mode_input == "move":
            logger.log_message("Mode : move", status='INFO')
            return True
        elif mode_input == "nomove":
            logger.log_message("Mode : nomove", status='INFO')
            return False
        else:
            print("Invalid input. Please enter 'move' or 'nomove'.")


def build_notification_message(mode_str: str, ip_list: List[str], 
                              file_map: Dict[str, str], 
                              success_count: Optional[int] = None,
                              total_count: Optional[int] = None,
                              duration: Optional[int] = None,
                              successful_ips: Optional[Set[str]] = None,
                              completed_ip: Optional[str] = None,
                              move_mode: Optional[bool] = None) -> str:
    """Build notification message."""
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    # Build file deployment plan section
    file_plan = "File deployment plan :\n"
    for idx, (filename, remote_path) in enumerate(file_map.items(), 1):
        if move_mode is not None:
            if move_mode:
                # Move mode: file will be moved to original name (no .BMT in final path)
                remote_file_path = os.path.join(remote_path, filename)
            else:
                # Nomove mode: file stays with .BMT extension
                remote_file_path = make_remote_file_path(remote_path, filename)
        else:
            # Fallback if move_mode not provided
            remote_file_path = make_remote_file_path(remote_path, filename)
        file_plan += f"  [{idx}] {filename} -> {remote_file_path}\n"
    
    if duration is not None:
        # Completion message
        message = f"Deploy complete.\n\n"
        message += f"Time : {timestamp}\n"
        message += f"Mode : {mode_str}\n"
        message += f"IP : {total_count}\n"
        message += f"Duration : {duration}s\n\n"
        message += file_plan
    elif success_count is not None and total_count is not None:
        # Progress message
        if completed_ip:
            message = f"IP {completed_ip} completed.\n\n"
        else:
            message = ""
        message += f"Time : {timestamp}\n"
        message += f"Mode : {mode_str}\n"
        message += f"Progress : {success_count}/{total_count}\n"
        
        # Remaining IP list
        if successful_ips and success_count < total_count:
            remaining = [ip for ip in ip_list if ip not in successful_ips]
            message += "\n[IP List]\n"
            for ip in remaining:
                message += f"  {ip}\n"
        
        # File list
        message += "\n[File]\n"
        for filename in file_map.keys():
            message += f"  {filename}\n"
        
        message += "\n" + file_plan
    else:
        # Start message
        message = f"Deploy started.\n\n"
        message += f"Time : {timestamp}\n"
        message += f"Mode : {mode_str}\n"
        message += f"IP : {total_count}\n"
        
        # IP list
        message += "\n[IP List]\n"
        for ip in ip_list:
            message += f"  {ip}\n"
        
        # File list
        message += "\n[File]\n"
        for filename in file_map.keys():
            message += f"  {filename}\n"
        
        message += "\n" + file_plan
    
    return message


def main() -> None:
    """
    Main deployment function.
    Deploys file to all IP with infinite retry until all succeed.
    
    Process:
    1. Load configuration
    2. Read IP list and file mapping
    3. Remove host keys for all IP
    4. Process each IP in parallel (retries until success)
    5. Send notifications and print statistics
    """
    config = load_config()
    
    stats = DeploymentStats()
    stats.record_reset()
    
    # Step 1: Get mode input first
    move_mode = get_mode_input()
    
    # Step 2: Initialize log file
    logger.init_log_file()
    
    try:
        # Validate required directories and file
        if not os.path.exists(FILE_DIR):
            logger.log_message(f"Error : {FILE_DIR} missing", status='FAILED')
            sys.exit(1)
        
        ip_list = read_ip_list(IP_TXT)
        if not ip_list:
            logger.log_message(f"Error : {IP_TXT} empty", status='FAILED')
            sys.exit(1)
        
        file_map = read_file(FILE_TXT)
        if not file_map:
            logger.log_message(f"Error : {FILE_TXT} empty", status='FAILED')
            sys.exit(1)
        
        # Step 3: Display file and remote path information
        logger.log_message("File deployment plan :", status='INFO')
        for idx, (filename, remote_path) in enumerate(file_map.items(), 1):
            if move_mode:
                # Move mode: file will be moved to original name (no .BMT in final path)
                remote_file = os.path.join(remote_path, filename)
            else:
                # Nomove mode: file stays with .BMT extension
                remote_file = make_remote_file_path(remote_path, filename)
            logger.log_message(f"  [{idx}] {filename} -> {remote_file}", status='INFO')
        logger.log_message("")
        
        stats.total_ip = len(ip_list)
        
        # Remove host keys for all IP
        for ip in ip_list:
            if ip and not ip.startswith('#'):
                remove_host_key(ip, config)
        
        init_complete_file()
        
        if config.get('notification', {}).get('enabled', False) and 'start' in config.get('notification', {}).get('notify_on', []):
            mode_str = "Move" if move_mode else "Nomove"
            email_subject = f"Deploy Started - {len(ip_list)} IP"
            email_message = build_notification_message(mode_str, ip_list, file_map, total_count=len(ip_list), move_mode=move_mode)
            send_notification(config, email_subject, email_message, ['start'])
        
        num_workers = len(ip_list)
        logger.log_message(f"Starting : {len(ip_list)} IP, {num_workers} thread", status='INFO')
        logger.log_message("")
        
        success_ip: Set[str] = set()
        retry_interval = config['retry']['interval']
        main_start_time = time.time()
        
        retry_round = 0
        while len(success_ip) < len(ip_list):
            remaining_ip = [ip for ip in ip_list if ip not in success_ip]
            
            if not remaining_ip:
                break
            
            retry_round += 1
            if retry_round > 1:
                logger.log_message(f"Retry round {retry_round} ({len(remaining_ip)} remaining)", status='INFO')
            
            try:
                with ThreadPoolExecutor(max_workers=num_workers) as executor:
                    futures = {
                        executor.submit(process_single_ip, ip, file_map, move_mode, config, stats): ip 
                        for ip in remaining_ip
                    }
                    
                    try:
                        for future in as_completed(futures):
                            ip = futures[future]
                            try:
                                result = future.result()
                                if result:
                                    success_ip.add(ip)
                                    record_complete_ip(ip)
                                    logger.log_message(f"Done ({len(success_ip)}/{len(ip_list)})", ip, 'SUCCESS')
                                    
                                    if (config.get('notification', {}).get('enabled', False) and 
                                        'ip_success' in config.get('notification', {}).get('notify_on', [])):
                                        mode_str = "Move" if move_mode else "Nomove"
                                        email_subject = f"IP {ip} Completed"
                                        email_message = build_notification_message(
                                            mode_str, ip_list, file_map,
                                            success_count=len(success_ip),
                                            total_count=len(ip_list),
                                            successful_ips=success_ip,
                                            completed_ip=ip,
                                            move_mode=move_mode
                                        )
                                        send_notification(config, email_subject, email_message, ['ip_success'])
                                else:
                                    logger.log_message("Failed", ip, 'FAILED')
                            except Exception as e:
                                logger.log_message(f"Error : {type(e).__name__}", ip, 'FAILED')
                    except KeyboardInterrupt:
                        logger.log_message("Interrupted by user", status='WARNING')
                        raise
            except KeyboardInterrupt:
                logger.log_message("Interrupted by user", status='WARNING')
                raise
            
            if len(success_ip) < len(ip_list):
                time.sleep(retry_interval)
        
        stats.end_time = time.time()
        total_elapsed = int(time.time() - main_start_time)
        logger.log_message(f"Done ({len(success_ip)}/{len(ip_list)} IP, {total_elapsed}s)", status='SUCCESS')
        
        print_statistics(stats)
        
        if config.get('notification', {}).get('enabled', False):
            notification_config = config.get('notification', {})
            notify_on = notification_config.get('notify_on', [])
            if 'complete' in notify_on and len(success_ip) == len(ip_list):
                mode_str = "Move" if move_mode else "Nomove"
                email_subject = f"Deploy Complete - {len(success_ip)}/{len(ip_list)} IP"
                email_message = build_notification_message(mode_str, ip_list, file_map, 
                                                     total_count=len(ip_list), 
                                                     duration=total_elapsed,
                                                     move_mode=move_mode)
                send_notification(config, email_subject, email_message, ['complete'])
    
    finally:
        logger.close()


if __name__ == "__main__":
    main()
