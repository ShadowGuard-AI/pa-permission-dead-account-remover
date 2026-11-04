# pa-permission-dead-account-remover

An identifier and reporter for dead account permission candidates. It identifies and reports files that are candidates for permission removal because they are owned by inactive or terminated user accounts, or by an owner uid that resolves to no account at all. It changes nothing: no permission, ACL, or account state is modified in any mode, and every report says so plainly. A file is a candidate when its owner, read with os.stat and resolved with pwd, is one of the named users, or when its owner uid has no account. The basis is reported per file. File paths are never used as the test, so a file that merely sits under a folder named for a user is not a candidate. Focused on tools for analyzing and assessing file system permissions.

## Install

```
git clone https://github.com/ShadowGuard-AI/pa-permission-dead-account-remover.git
cd pa-permission-dead-account-remover
pip install -r requirements.txt
```

## Usage

```
python3 main.py -d /path/to/directory -u users.txt [options]
```

## Parameters

- `-d, --directory`: Required. The directory to analyze and report candidates in. Nothing in it is changed.
- `-u, --users`: Required. Path to a file containing a list of inactive/terminated users (one username per line). An empty user list is refused at startup.
- `-r, --remove`: Report removal candidates for the inactive users. This mode reports candidates only and changes no permissions. A run in this mode that matches nothing exits 1 with a nothing matched line. Without this flag, the tool identifies candidate files in the same way.
- `-l, --log-file`: Path to a log file for recording actions and errors.
- `-e, --exclude`: Path to a file containing a list of path patterns to exclude (one pattern per line, using .gitignore syntax).

Every run counts and prints the files scanned and the candidates matched. No permissions were changed by any run of this tool.

## Verified in this wave

`python3 main.py --help` could not run in this sandbox: it exits 1 with "Error: Missing dependencies: No module named 'pathspec'. Please install them using 'pip install pathspec rich'" because those packages are not installed and installs are not made in this wave. Parameters above are taken from the argument parser in `main.py`, and `main.py` passes `py_compile`. No live candidate run is claimed.

## License

See LICENSE.
