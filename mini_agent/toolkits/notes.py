from pathlib import Path


class NotesStore:
    def __init__(self, path: Path):
        self.path = path

    def save(self, text: str) -> str:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8") as file:
            file.write(text.strip() + "\n")

        return "笔记已保存。"

    def read(self) -> str:
        if not self.path.exists():
            return "暂无笔记。"

        notes = [line.strip() for line in self.path.read_text(encoding="utf-8").splitlines()]
        notes = [line for line in notes if line]
        if not notes:
            return "暂无笔记。"

        formatted = "\n".join(f"{index}. {note}" for index, note in enumerate(notes, 1))
        return f"笔记:\n{formatted}"
