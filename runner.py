from time import sleep
from datetime import datetime, timedelta
import os 
from pathlib import Path

executables = ["copernicusS2.py", "copernicusS3_updated.py"]
times_to_run = [""]

# Check if all files exist

def check_files_exist(executables: list):
    current_dir = os.getcwd()
    for element in executables:
        file_path = Path(current_dir) / element
        if not file_path.exists():
            raise ValueError(f"{element} does not exist in {current_dir}")
    print(f"All {len(executables)} executables exist in {current_dir}")

# Execute them 

def run_files(executables: list):
    current_dir = os.getcwd()
    for element in executables:
        # Use 'python3' instead of 'python'
        if os.system(f'python3 {element}'):
            raise ValueError(f"{element} does not exist or failed to run in {current_dir}")
    print(f"All {len(executables)} executables found and ran")


def single_run(executables=executables): # For single runs
    check_files_exist(executables)
    run_files(executables)


def permanent_run(interval=43200, executables=executables): 
    """
    For running permanently each 12h starting from current time
    By default will use 12h intervals 
    for 24h use 86400
    """
    while True:
        check_files_exist(executables)
        run_files(executables)
        print(f"Waiting {interval} seconds for next run")
        sleep(interval)


def run_at_hour(target_hour=12, executables=executables):
    """
    Runs the check and execution of files every day at a specific target hour.

    :param target_hour: The hour at which the script should run every day (0-23).
    :param executables: List of executable files to check and run.
    """
    while True:
        now = datetime.now()

        # Set the target time (same day if target hour is still ahead, or next day)
        target_time = now.replace(hour=target_hour, minute=0, second=0, microsecond=0)
        if now > target_time:
            # If the target time has already passed today, set it for tomorrow
            target_time += timedelta(days=1)
        
        wait_time = (target_time - now).total_seconds()
        
        print(f"Waiting {wait_time // 3600} hours and {(wait_time % 3600) // 60} minutes for the next run at {target_time.strftime('%H:%M')}")
        sleep(wait_time)
        
        check_files_exist(executables)
        run_files(executables)

#single_run()
#permanent_run()
run_at_hour(target_hour=12)
