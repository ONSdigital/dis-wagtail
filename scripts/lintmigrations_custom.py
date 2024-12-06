import subprocess
import sys  # To get the absolute path to the currently running Python interpreter
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent

# Extract the app label from the directory structure
def get_app_labels():
    return [
        path.parent.name
        for path in Path(BASE_DIR / "cms").glob("*/migrations")
    ]


# Run the lintmigrations command for a given app_label
def run_lintmigration(app_label):
    try:
        result = subprocess.run(  # noqa: S603
            [sys.executable, BASE_DIR / "manage.py", "lintmigrations", app_label],
            text=True,
            capture_output=True,
            check=True,
        )
        output = f"\nRunning lintmigrations for {app_label} succeeded \n{result.stdout}"
        exit_code = result.returncode
    except subprocess.CalledProcessError as e:
        output = f"\nRunning lintmigrations for {app_label} failed \n{e.stdout or ''}{e.stderr or ''}"
        exit_code = e.returncode
    return exit_code, output


def run_lintmigrations_in_threads(labels):
    exit_codes = []
    # Use ThreadPoolExecutor for parallel execution
    with ThreadPoolExecutor() as executor:
        futures = {executor.submit(run_lintmigration, label): label for label in labels}

        for future in as_completed(futures):
            exit_code, output = future.result()
            # Print the output of each completed future in order
            print(output)
            exit_codes.append(exit_code)

    return exit_codes


if __name__ == "__main__":
    app_labels = get_app_labels()

    print("Apps we are linting: \n", app_labels)

    check_exit_codes = run_lintmigrations_in_threads(app_labels)
    # Check if any exit code is non-zero
    if any(code != 0 for code in check_exit_codes):
        print("One or more migrations linting failed.")
        sys.exit(1)

    print("All migrations linted successfully.")
    sys.exit(0)
