def confirm_in_terminal(prompt: str) -> bool:
    try:
        answer = input(prompt).strip().lower()
    except EOFError:
        return False

    return answer in {"y", "yes"}
