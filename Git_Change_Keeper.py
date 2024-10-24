import os
import git
import argparse
from datetime import datetime
import hashlib
import time

# Function to calculate the hash of the file content
def calculate_hash(content):
    return hashlib.sha256(content.encode('utf-8')).hexdigest()

# Load saved hashes from file
def load_saved_hashes(hash_store_path):
    if os.path.exists(hash_store_path):
        with open(hash_store_path, 'r') as f:
            return dict(line.strip().split(' ', 1) for line in f)
    return {}

# Save hashes to file
def save_hashes(hashes, hash_store_path):
    with open(hash_store_path, 'w') as f:
        for file_path, file_hash in hashes.items():
            f.write(f'{file_path} {file_hash}\n')

# Create hash file and folder if they do not exist
def ensure_hash_store_exists(output_base_path, hash_store_path):
    if not os.path.exists(output_base_path):
        os.makedirs(output_base_path)  # Create the folder for saving changes
    if not os.path.exists(hash_store_path):
        open(hash_store_path, 'w').close()

# Save git changes detected in the repository
def save_git_changes(repo_path, output_base_path, hash_store_path):
    # Open the Git repository
    repo = git.Repo(repo_path)

    # Check if there are changes
    if repo.is_dirty(untracked_files=True):
        # Get the difference between the last commit and the current state
        diff_files = repo.git.diff(None, name_only=True).splitlines()

        # Load previous hashes
        saved_hashes = load_saved_hashes(hash_store_path)
        new_hashes = {}

        changes_saved = False

        # First check if there are files with new changes
        for file_path in diff_files:
            file_path = file_path.strip()  # Trim extra spaces
            if file_path:
                # Check if the file exists in the working directory
                full_file_path = os.path.join(repo_path, file_path)
                if os.path.exists(full_file_path):
                    try:
                        # Call git diff with "--" added before the path
                        diff_content = repo.git.diff('--', file_path)

                        # Calculate the hash of the new content
                        current_hash = calculate_hash(diff_content)

                        # If the content has changed, mark it
                        if file_path not in saved_hashes or saved_hashes[file_path] != current_hash:
                            # If there are new changes, create a new folder
                            if not changes_saved:
                                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                                output_path = os.path.join(output_base_path, f'changes_{timestamp}')
                                os.makedirs(output_path, exist_ok=True)
                            # Save the changes to a .diff file
                            with open(os.path.join(output_path, f'{os.path.basename(file_path)}.diff'), 'w') as f:
                                f.write(diff_content)

                            # Save the new hash
                            new_hashes[file_path] = current_hash
                            changes_saved = True

                    except git.exc.GitCommandError as e:
                        print(f"Error with file {file_path}: {e}")
                else:
                    print(f"File does not exist in the repository: {file_path}")

        if changes_saved:
            print(f'Changes saved in folder: {output_path}')
            # Update hashes
            saved_hashes.update(new_hashes)
            save_hashes(saved_hashes, hash_store_path)
        else:
            print('No new changes to save.')
    else:
        print('No changes detected.')

# Function to validate interval input
def positive_int(value):
    ivalue = int(value)
    if ivalue <= 0 or ivalue > 100000:
        raise argparse.ArgumentTypeError("Interval must be positive and not exceed 100000 seconds.")
    return ivalue

# Main function for periodic monitoring
def monitor_repo(repo_path, check_interval, output_base_path):
    hash_store_path = os.path.join(output_base_path, 'hashes.txt')
    ensure_hash_store_exists(output_base_path, hash_store_path)  # Check if the hash file and folder exist before starting monitoring
    while True:
        print(f'Checking for changes: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}')
        save_git_changes(repo_path, output_base_path, hash_store_path)
        # Delay between checks
        time.sleep(check_interval)

if __name__ == "__main__":
    # Create argument parser for command line arguments
    parser = argparse.ArgumentParser(description='Monitor a Git repository for changes.')
    parser.add_argument('repo_path', type=str, help='Path to the folder containing the Git repository')
    parser.add_argument('--interval', type=positive_int, default=600,
                        help='Check interval in seconds (must be positive and not exceed 100000, default is 600)')
    parser.add_argument('--output_path', type=str, default='Keeper_Of_Changes',
                        help='Path to the folder where changes will be saved (default is "Keeper_Of_Changes")')

    # Parse arguments
    args = parser.parse_args()

    # Call the monitoring function with the passed arguments
    monitor_repo(args.repo_path, args.interval, args.output_path)
