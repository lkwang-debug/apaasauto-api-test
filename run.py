import argparse
from configparser import ConfigParser
import os
import shutil
import socket
import subprocess
import sys
import time
import webbrowser
from pathlib import Path

try:
    import winreg
except ImportError:
    winreg = None


BASE_DIR = Path(__file__).resolve().parent
TEST_FILE = BASE_DIR / 'testcases' / 'test_all_api.py'
ALLURE_RESULTS_DIR = BASE_DIR / 'reports' / 'allure-results'
ALLURE_REPORT_DIR = BASE_DIR / 'reports' / 'allure-report'
CONFIG_FILE = BASE_DIR / 'data' / 'config.ini'


def build_pytest_command(pytest_args):
    command = [
        sys.executable,
        '-m',
        'pytest',
        str(TEST_FILE),
        '--alluredir',
        str(ALLURE_RESULTS_DIR),
    ]
    command.extend(pytest_args)
    return command


def ensure_clean_dir(path):
    if path.exists():
        shutil.rmtree(path)
    path.mkdir(parents=True, exist_ok=True)


def run_pytest(pytest_args):
    ensure_clean_dir(ALLURE_RESULTS_DIR)
    command = build_pytest_command(pytest_args)
    return subprocess.run(command, cwd=BASE_DIR).returncode


def is_recording_run(pytest_args):
    if not pytest_args:
        return True
    joined = ' '.join(pytest_args)
    return 'REC' in joined


def read_recording_config():
    parser = ConfigParser()
    parser.read(CONFIG_FILE, encoding='utf-8')
    return {
        'room_id': parser.get('recording', 'room_id', fallback=''),
        'room_name': parser.get('recording', 'room_name', fallback=''),
        'record_name': parser.get('recording', 'record_name', fallback=''),
        'min_record_seconds': parser.get('recording', 'min_record_seconds', fallback='10'),
        'retry_attempts': parser.get('recording', 'record_query_retry_attempts', fallback='37'),
        'retry_interval_seconds': parser.get('recording', 'record_query_retry_interval_seconds', fallback='5'),
    }


def confirm_recording_e2e_ready(no_prompt=False):
    config = read_recording_config()
    print('')
    print('Recording test precondition:')
    print(f"  room_id: {config['room_id']}")
    print(f"  room_name: {config['room_name']}")
    print(f"  record_name: {config['record_name']}")
    print(f"  recording duration: {config['min_record_seconds']} seconds")
    print(f"  file polling: {config['retry_attempts']} attempts, every {config['retry_interval_seconds']} seconds")
    print('')
    print('Please confirm a real client has already joined this room and stays online before the recording cases run.')
    print(f'Configure these values in: {CONFIG_FILE}')
    if no_prompt:
        print('--confirm-recording-ready is accepted for compatibility; recording tests now run without an input prompt.')


def find_allure_command():
    allure_cmd = shutil.which('allure') or shutil.which('allure.bat')
    if allure_cmd:
        return allure_cmd
    return None


def generate_allure_report():
    allure_cmd = find_allure_command()
    if not allure_cmd:
        print('Allure command not found in PATH.')
        return False

    command = [
        allure_cmd,
        'generate',
        str(ALLURE_RESULTS_DIR),
        '-o',
        str(ALLURE_REPORT_DIR),
        '--clean',
    ]
    completed = subprocess.run(command, cwd=BASE_DIR)
    return completed.returncode == 0


def find_free_port():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(('127.0.0.1', 0))
        return sock.getsockname()[1]


def find_chrome_path():
    env_path = os.environ.get('CHROME_PATH')
    if env_path and Path(env_path).exists():
        return env_path

    candidates = [
        Path(r'C:\Program Files\Google\Chrome\Application\chrome.exe'),
        Path(r'C:\Program Files (x86)\Google\Chrome\Application\chrome.exe'),
        Path(os.environ.get('LOCALAPPDATA', '')) / 'Google' / 'Chrome' / 'Application' / 'chrome.exe',
    ]
    for candidate in candidates:
        if candidate and candidate.exists():
            return str(candidate)

    if winreg is not None:
        try:
            with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r'Software\Microsoft\Windows\CurrentVersion\App Paths\chrome.exe') as key:
                value, _ = winreg.QueryValueEx(key, None)
                if value and Path(value).exists():
                    return value
        except OSError:
            pass
    return None


def start_report_server(port):
    creationflags = 0
    creationflags |= getattr(subprocess, 'CREATE_NEW_PROCESS_GROUP', 0)
    creationflags |= getattr(subprocess, 'DETACHED_PROCESS', 0)
    server_cmd = [
        sys.executable,
        '-m',
        'http.server',
        str(port),
        '--bind',
        '127.0.0.1',
    ]
    subprocess.Popen(
        server_cmd,
        cwd=ALLURE_REPORT_DIR,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        creationflags=creationflags,
    )
    time.sleep(1)
    return f'http://127.0.0.1:{port}'


def open_report(url, no_open=False):
    if no_open:
        return

    chrome_path = find_chrome_path()
    if chrome_path:
        subprocess.Popen([chrome_path, url], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return

    webbrowser.open(url)


def main():
    parser = argparse.ArgumentParser(description='Run APAAS API tests and open Allure report.')
    parser.add_argument('--no-open', action='store_true', help='generate allure report but do not open browser')
    parser.add_argument('--no-report', action='store_true', help='run pytest only and skip allure report generation')
    parser.add_argument('--report-port', type=int, default=0, help='fixed local port for report server, default auto-select')
    parser.add_argument(
        '--confirm-recording-ready',
        action='store_true',
        help='compatibility flag; recording tests now print a non-blocking client-join reminder',
    )
    args, pytest_args = parser.parse_known_args()

    if is_recording_run(pytest_args):
        confirm_recording_e2e_ready(no_prompt=args.confirm_recording_ready)

    pytest_code = run_pytest(pytest_args)

    if args.no_report:
        raise SystemExit(pytest_code)

    report_ok = generate_allure_report()
    if report_ok:
        port = args.report_port or find_free_port()
        report_url = start_report_server(port)
        print(f'Allure report directory: {ALLURE_REPORT_DIR}')
        print(f'Allure report url: {report_url}')
        open_report(report_url, no_open=args.no_open)
    else:
        print('Allure report generation failed.')

    raise SystemExit(pytest_code)


if __name__ == '__main__':
    main()
