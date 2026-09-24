def greet(name: str) -> str:
    if not name.strip():
        raise ValueError("name is required")
    return f"Hello, {name}!"

