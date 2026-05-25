from pathlib import Path

def solve_path(path: str) -> Path:
    # Fallback
    if isinstance(path, Path):
        return path
    
    # Normalizing
    path = Path(path.replace("\\", "/"))
    

    # Convertendo para Path
    absolute_path = Path.cwd() / path

    print(Path.cwd(), absolute_path)
    # Verification
    if not absolute_path.exists():
        raise ValueError(f"Path: {absolute_path} é inválido.")

    return absolute_path