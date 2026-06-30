
def chunk_markdown_by_heading(path: str) -> list[dict]:
    with open(path, "r", encoding="utf-8") as f:
        lines = f.readlines()

    chunks = []
    current_heading = "Intro"
    current_lines = []
    current_idx = 0
    
    def flush():
        if current_lines:
            chunks.append({
                "id": current_idx,
                "text": "".join(current_lines + current_heading ).strip(),
                "meta_data": {
                    "heading" : current_heading,
                }
            })

    for line in lines:
        stripped = line.lstrip("#").strip()
        is_heading = line.startswith("## ") or line.startswith("### ")

        if is_heading:
            flush()
            current_idx += 1
            current_heading = stripped
            current_lines = [line]
        else:
            current_lines.append(line)

    flush()
    return [c for c in chunks if c["content"]]
