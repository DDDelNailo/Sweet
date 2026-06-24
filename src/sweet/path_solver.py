from pathlib import Path

def solve_path(path: str | Path) -> Path:
    # Fallback
    if isinstance(path, Path):
        return path
    
    # Normalizing
    norm_path = Path(path.replace("\\", "/"))

    # Convertendo para Path
    absolute_path = Path.cwd() / norm_path

    # Verification
    if not absolute_path.exists():
        raise ValueError(f"Path: {absolute_path} é inválido.")

    return absolute_path