from datetime import datetime
from os import makedirs
log_dir = "logs"

makedirs(log_dir, exist_ok=True)

log_file = open("logs/logs.txt" , 'a')
def log(log_message:str):
    """
    Writes the logs to the terminal and logs.txt file

    ARGS:
        log_message (str): The message to be logged

    RETURNS:
        NIL
    """
    print(log_message)
    # get current time
    current_time = datetime.now()
    time_formatted = current_time.strftime("%H:%M:%S")
    # format the log with current time for the logs.txt file
    file_message = f"[{time_formatted}] > {log_message}"
    log_file.write(file_message + '\n')
    log_file.flush()