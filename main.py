#!/usr/bin/env python3
import argparse
import logging
import os
import pwd
import sys
from typing import List, Optional, Tuple

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
        description="Identifies and reports files that are candidates for permission removal because they are owned by inactive or terminated user accounts, or by an owner uid with no account. This tool changes nothing: it only reports candidates."
    )

    parser.add_argument(
        "-d",
        "--directory",
        type=str,
        required=True,
        help="The directory to analyze and report candidates in. Nothing in it is changed.",
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
        help="Report removal candidates for the inactive users. This mode reports candidates only and changes no permissions. Without this flag, the tool identifies candidate files in the same way.",
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


def candidate_basis(filepath: str, users: List[str]) -> Optional[str]:
    """
    Returns why a file is a candidate, or None when it is not.

    A file is a candidate when its owner, read with os.stat and resolved
    with pwd, is one of the named users, or when its owner uid resolves
    to no account at all. The file path itself is never used as a test.
    """
    uid = os.stat(filepath).st_uid
    try:
        owner = pwd.getpwuid(uid).pw_name
    except KeyError:
        return f"owner uid {uid} has no account"
    if owner in users:
        return f"owned by named user {owner} (uid {uid})"
    return None


def find_candidates(directory: str, users: List[str], exclude_spec: Optional[pathspec.PathSpec] = None) -> Tuple[List[Tuple[str, str]], int]:
    """
    Finds candidate files in the given directory for the specified users.

    Returns:
        A pair: a list of (filepath, basis) candidates, and the number
        of files scanned.
    """
    candidates = []
    scanned = 0
    for root, _, files in os.walk(directory):
        for file in files:
            filepath = os.path.join(root, file)

            if exclude_spec and exclude_spec.match_file(filepath):
                logging.debug(f"Skipping excluded path: {filepath}")
                continue

            scanned += 1
            try:
                basis = candidate_basis(filepath, users)
                if basis:
                    candidates.append((filepath, basis))
                    logging.info(f"Candidate file: {filepath} ({basis})")
            except Exception as e:
                logging.error(f"Error checking ownership for {filepath}: {e}")

    return candidates, scanned


def check_permissions(directory: str, users: List[str], exclude_spec: Optional[pathspec.PathSpec] = None) -> Tuple[List[Tuple[str, str]], int]:
    """Identifies candidate files. Changes nothing."""
    return find_candidates(directory, users, exclude_spec)


def report_removal_candidates(directory: str, users: List[str], exclude_spec: Optional[pathspec.PathSpec] = None) -> Tuple[List[Tuple[str, str]], int]:
    """
    Reports removal candidate files. Changes nothing: no permission,
    ACL, or account state is modified by this tool in any mode.
    """
    candidates, scanned = find_candidates(directory, users, exclude_spec)
    for filepath, basis in candidates:
        print(f"Removal candidate: {filepath} ({basis}). No permissions were changed.")
        logging.info(f"Removal candidate: {filepath} ({basis}). No permissions were changed.")
    return candidates, scanned


def main() -> None:
    """
    Main function to execute the candidate identification and reporting tool.
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

    if not users:
        rprint("[red]Error: The user list is empty. No users were named, so no report was run.[/red]")
        logging.error("Empty user list refused at startup.")
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
        rprint("[yellow]Reporting removal candidates. This tool changes nothing.[/yellow]")
        candidates, scanned = report_removal_candidates(args.directory, users, exclude_spec)
        rprint(f"[yellow]Files scanned: {scanned}. Removal candidates matched: {len(candidates)}.[/yellow]")
        if scanned == 0:
            rprint("[red]No files were scanned. Nothing matched.[/red]")
            logging.error("Remove report run scanned no files.")
            sys.exit(1)
        if not candidates:
            rprint("[red]Nothing matched. No removal candidates were found.[/red]")
            logging.error("Remove report run matched nothing.")
            sys.exit(1)
        rprint("[green]Removal candidate reporting completed. No permissions were changed.[/green]")
        logging.info("Removal candidate reporting completed. No permissions were changed.")
    else:
        rprint("[yellow]Identifying candidate files. This tool changes nothing.[/yellow]")
        candidates, scanned = check_permissions(args.directory, users, exclude_spec)
        rprint(f"[yellow]Files scanned: {scanned}. Candidate files matched: {len(candidates)}.[/yellow]")
        if scanned == 0:
            rprint("[red]No files were scanned. Nothing matched.[/red]")
            logging.error("Check run scanned no files.")
            sys.exit(1)
        if candidates:
            rprint("[red]The following files are candidates because of their ownership:[/red]")
            for filepath, basis in candidates:
                rprint(f"[blue]{filepath} ({basis})[/blue]")
        else:
            rprint("[green]No candidate files found for the specified users.[/green]")
        rprint("[green]Candidate identification completed. No permissions were changed.[/green]")
        logging.info("Candidate identification completed. No permissions were changed.")

if __name__ == "__main__":
    main()