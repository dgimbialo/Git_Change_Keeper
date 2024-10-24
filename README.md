# Git_Change_Keeper
This Python script monitors a specified Git repository for changes and saves the detected differences into an output directory. The script calculates hashes for the differences and stores them, allowing it to detect new changes on subsequent runs. The script runs periodically based on a specified interval. It supports custom paths for both the Git repository and the output directory where changes are saved. The user can also configure the monitoring interval.

How to Use
Install Dependencies: Ensure you have the required libraries installed. You can install them using the following:

bash
Copy code
pip install gitpython
Running the Script: To run the script, use the following command:

bash
Copy code
python monitor_git.py <repo_path> [--interval <check_interval>] [--output_path <output_directory>]
<repo_path>: Path to the folder containing the Git repository.
--interval (optional): Monitoring interval in seconds. It must be a positive integer and less than or equal to 100000. The default is 600 seconds.
--output_path (optional): Path to the folder where changes will be saved. The default is Keeper_Of_Changes.
Example:

bash
Copy code
python monitor_git.py /path/to/repo --interval 300 --output_path /path/to/output
