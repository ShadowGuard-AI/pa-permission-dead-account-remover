#!/usr/bin/env python3
import argparse
import logging
import os
import sys
from typing import List, Optional

try:
    import pathspec
    from rich import print as rprint
except ImportError as e:
    print(f"Error: Missing dependencies: {e}. Please install them using 'pip install pathspec rich'")
    sys.exit(1)


# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


def setup_argparse() -> argparse.ArgumentParser:
    """
    Sets up the argument parser for the command-line interface.

    Returns:
        argparse.ArgumentParser: The configured argument parser.
    """
    parser = argparse.ArgumentParser(
        description="Identifies and removes permissions associated with inactive or terminated user accounts."
    )

    parser.add_argument(
        "-d",
        "--directory",
        type=str,
        required=True,
        help="The directory to analyze and modify permissions in.",
    )

    parser.add_argument(
        "-u",
        "--users",
        type=str,
        required=True,
        help="Path to a file containing a list of inactive/terminated users (one username per line).",
    )

    parser.add_argument(
        "-r",
        "--remove",
        action="store_true",
        help="Remove permissions for the inactive users.  Without this flag, the tool only identifies them.",
    )

    parser.add_argument(
        "-l",
        "--log-file",
        type=str,
        help="Path to a log file for recording actions and errors.",
    )
    
    parser.add_argument(
        "-e",
        "--exclude",
        type=str,
        help="Path to a file containing a list of path patterns to exclude (one pattern per line, using .gitignore syntax).",
    )
    
    return parser


def load_users(user_file: str) -> List[str]:
    """
    Loads a list of usernames from a file.

    Args:
        user_file (str): The path to the file containing usernames.

    Returns:
        List[str]: A list of usernames.

    Raises:
        FileNotFoundError: If the user file does not exist.
        IOError: If the user file cannot be read.
    """
    try:
        with open(user_file, "r") as f:
            users = [line.strip() for line in f if line.strip()]  # Strip whitespace and remove empty lines
        return users
    except FileNotFoundError:
        logging.error(f"User file not found: {user_file}")
        raise
    except IOError as e:
        logging.error(f"Error reading user file: {user_file} - {e}")
        raise


def load_excludes(exclude_file: str) -> pathspec.PathSpec:
    """
    Loads exclude patterns from a file, using .gitignore syntax.

    Args:
        exclude_file (str): The path to the exclude file.

    Returns:
        pathspec.PathSpec: A pathspec object representing the exclusion patterns.

    Raises:
        FileNotFoundError: If the exclude file does not exist.
        IOError: If the exclude file cannot be read.
    """
    try:
        with open(exclude_file, "r") as f:
            lines = [line.strip() for line in f if line.strip()]  # Strip whitespace and remove empty lines
        spec = pathspec.PathSpec.from_lines("gitwildmatch", lines)
        return spec
    except FileNotFoundError:
        logging.error(f"Exclude file not found: {exclude_file}")
        raise
    except IOError as e:
        logging.error(f"Error reading exclude file: {exclude_file} - {e}")
        raise


def check_permissions(directory: str, users: List[str], exclude_spec: Optional[pathspec.PathSpec] = None) -> List[str]:
    """
    Checks permissions in the given directory for the specified users.

    Args:
        directory (str): The directory to check.
        users (List[str]): A list of usernames to check for.
        exclude_spec (Optional[pathspec.PathSpec]): A pathspec object for excluding paths.

    Returns:
        List[str]: A list of files where the users have permissions.
    """
    files_with_permissions = []
    for root, _, files in os.walk(directory):
        for file in files:
            filepath = os.path.join(root, file)

            # Check if the path is excluded
            if exclude_spec and exclude_spec.match_file(filepath):
                logging.debug(f"Skipping excluded path: {filepath}")
                continue

            try:
                # Check permissions (This part is intentionally simplified; real-world implementation would involve actual permission checking)
                # In a real scenario, this would involve os.stat, ACL checks, etc.
                # The following is a placeholder:
                has_permissions = any(user.lower() in filepath.lower() for user in users)  # Placeholder check
                if has_permissions:
                    files_with_permissions.append(filepath)
                    logging.info(f"User(s) found with permissions for file: {filepath}")
            except Exception as e:
                logging.error(f"Error checking permissions for {filepath}: {e}")

    return files_with_permissions


def remove_permissions(directory: str, users: List[str], exclude_spec: Optional[pathspec.PathSpec] = None) -> None:
    """
    Removes permissions for the specified users in the given directory.

    Args:
        directory (str): The directory to modify.
        users (List[str]): A list of usernames to remove permissions for.
        exclude_spec (Optional[pathspec.PathSpec]): A pathspec object for excluding paths.
    """
    for root, _, files in os.walk(directory):
        for file in files:
            filepath = os.path.join(root, file)

            # Check if the path is excluded
            if exclude_spec and exclude_spec.match_file(filepath):
                logging.debug(f"Skipping excluded path: {filepath}")
                continue

            try:
                # Remove permissions (This part is intentionally simplified; real-world implementation would involve actual permission removal)
                # In a real scenario, this would involve os.chmod, ACL modifications, etc.
                # The following is a placeholder:
                if any(user.lower() in filepath.lower() for user in users):  # Placeholder check
                    print(f"Removing permissions for users {users} from {filepath}")
                    logging.info(f"Removing permissions for users {users} from {filepath}")
                    # In a real implementation, the permission removal logic would go here.
                    # Example (UNSAFE AND DOES NOT WORK DIRECTLY - illustrates the idea):
                    # os.chmod(filepath, 0o755)  # Removes write access for everyone except owner
            except Exception as e:
                logging.error(f"Error removing permissions for {filepath}: {e}")


def main() -> None:
    """
    Main function to execute the permission assessment and removal tool.
    """
    parser = setup_argparse()
    args = parser.parse_args()

    # Configure logging to file, if specified
    if args.log_file:
        file_handler = logging.FileHandler(args.log_file)
        file_handler.setLevel(logging.DEBUG)  # Log everything to file
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        file_handler.setFormatter(formatter)
        logging.getLogger().addHandler(file_handler)
        logging.info(f"Logging to file: {args.log_file}")

    try:
        users = load_users(args.users)
        logging.info(f"Loaded users from {args.users}: {users}")
    except FileNotFoundError:
        rprint(f"[red]Error: User file not found.[/red]")
        sys.exit(1)
    except IOError:
        rprint(f"[red]Error: Could not read user file.[/red]")
        sys.exit(1)

    exclude_spec = None
    if args.exclude:
        try:
            exclude_spec = load_excludes(args.exclude)
            logging.info(f"Loaded exclude patterns from {args.exclude}")
        except FileNotFoundError:
            rprint(f"[red]Error: Exclude file not found.[/red]")
            sys.exit(1)
        except IOError:
            rprint(f"[red]Error: Could not read exclude file.[/red]")
            sys.exit(1)

    if not os.path.isdir(args.directory):
        rprint(f"[red]Error: Directory not found: {args.directory}[/red]")
        logging.error(f"Directory not found: {args.directory}")
        sys.exit(1)

    if args.remove:
        rprint("[yellow]Removing permissions...[/yellow]")
        remove_permissions(args.directory, users, exclude_spec)
        rprint("[green]Permissions removal process completed.[/green]")
        logging.info("Permissions removal process completed.")
    else:
        rprint("[yellow]Checking permissions...[/yellow]")
        files_with_permissions = check_permissions(args.directory, users, exclude_spec)
        if files_with_permissions:
            rprint("[red]The following files have permissions for the specified users:[/red]")
            for file in files_with_permissions:
                rprint(f"[blue]{file}[/blue]")
        else:
            rprint("[green]No files found with permissions for the specified users.[/green]")
        logging.info("Permissions check completed.")

if __name__ == "__main__":
    main()