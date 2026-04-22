import subprocess
import sys
import os
from pathlib import Path


def _candidate_python_paths(base_dir: Path):
	if sys.executable:
		yield Path(sys.executable)
	if sys.platform.startswith("win"):
		yield base_dir / ".venv313" / "Scripts" / "python.exe"
		yield base_dir / ".venv" / "Scripts" / "python.exe"
	else:
		yield base_dir / ".venv313" / "bin" / "python"
		yield base_dir / ".venv" / "bin" / "python"


def _can_run_django(python_path: Path) -> bool:
	if not python_path.exists():
		return False
	probe = [
		str(python_path),
		"-c",
		"import django, dotenv; print('ok')",
	]
	try:
		completed = subprocess.run(probe, capture_output=True, text=True, timeout=10, check=False)
		return completed.returncode == 0
	except (OSError, subprocess.SubprocessError):
		return False


def _resolve_python(base_dir: Path) -> str:
	for candidate in _candidate_python_paths(base_dir):
		if _can_run_django(candidate):
			return str(candidate)
	return sys.executable


def main():
	base_dir = Path(__file__).resolve().parent
	manage_py = base_dir / "elearning_project" / "manage.py"
	if not manage_py.exists():
		raise FileNotFoundError(f"manage.py not found at: {manage_py}")

	python_exec = _resolve_python(base_dir)
	runserver_args = sys.argv[1:] or ["runserver", "localhost:8000"]
	env = os.environ.copy()

	# Keep production settings strict, but avoid HTTPS redirect loops on local Django dev server.
	if runserver_args and runserver_args[0] == "runserver":
		env.setdefault("DJANGO_DEBUG", "1")
		env.setdefault("DJANGO_SECURE_SSL_REDIRECT", "0")
		env.setdefault("DJANGO_SESSION_COOKIE_SECURE", "0")
		env.setdefault("DJANGO_CSRF_COOKIE_SECURE", "0")
		if "--insecure" not in runserver_args:
			runserver_args.append("--insecure")

	result = subprocess.run(
		[python_exec, str(manage_py), *runserver_args],
		cwd=str(base_dir / "elearning_project"),
		env=env,
		check=False,  # Don't raise exception; handle exit code below
	)
	
	if result.returncode != 0:
		print(f"✗ Django server exited with code {result.returncode}", file=sys.stderr)
		print(f"  Command: {' '.join(runserver_args)}", file=sys.stderr)
		print(f"  Working directory: {base_dir / 'elearning_project'}", file=sys.stderr)
		print(f"  Check your Django settings, migrations, and dependencies.", file=sys.stderr)
		sys.exit(result.returncode)


if __name__ == "__main__":
	main()
