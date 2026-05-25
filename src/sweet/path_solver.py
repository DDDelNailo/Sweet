from pathlib import Path

def solve_path(path: str) -> Path:
    # Fallback
    if isinstance(path, Path):
        return path
    
    # Normalizing
    path = Path(path.replace("\\", "/"))
    
    # Convertendo para Path
    absolute_path = Path.cwd() / path

    # Verification
    if not absolute_path.exists():
        raise ValueError("Path inválido")

    return absolute_path