import os
import subprocess
import sys  # To get the absolute path to the currently running Python interpreter
from concurrent.futures import ThreadPoolExecutor, as_completed


# Extract the app label from the directory structure
def get_app_labels():
    app_labels = []
    for root, dirs, _files in os.walk("../cms"):
        if "migrations" in dirs:
            app_label = root.split(os.sep)[-1]
            app_labels.append(app_label)
    return app_labels


# Run the lintmigrations command for a given app_label
def run_lintmigration(app_label):
    try:
        result = subprocess.run(
            [sys.executable, "python", "../manage.py", "lintmigrations", app_label],
            text=True,
            capture_output=True,
            check=True,
        )
        output = f"\nRunning lintmigrations for {app_label}\n{result.stdout}"
    except subprocess.CalledProcessError as e:
        output = f"\nRunning lintmigrations for {app_label}\n{e.stdout or ''}{e.stderr or ''}"
    return output


def run_lintmigrations_in_parallel(app_labels):
    # Use ThreadPoolExecutor for parallel execution
    with ThreadPoolExecutor() as executor:
        futures = {executor.submit(run_lintmigration, app_label): app_label for app_label in app_labels}

        for future in as_completed(futures):
            # Print the output of each completed future in order
            print(future.result())


if __name__ == "__main__":
    app_labels = get_app_labels()

    print("Apps we are linting: \n", app_labels)

    run_lintmigrations_in_parallel(app_labels)
