
#切割纯文本
def split_text(text: str, chunk_size: int = 500, overlap: int = 50) -> list[str]:
    """把一段文本按固定长度切成 chunks，并保留指定 overlap。"""
    if chunk_size <= 0:
        raise ValueError("chunk_size 必须大于 0")

    if overlap < 0:
        raise ValueError("overlap 不能小于 0")

    if overlap >= chunk_size:
        raise ValueError("overlap 必须小于 chunk_size")

    cleaned_text = text.strip()
    if not cleaned_text:
        return []

    chunks: list[str] = []
    start = 0

    while start < len(cleaned_text):
        end = start + chunk_size
        chunk = cleaned_text[start:end].strip()

        if chunk:
            chunks.append(chunk)

        if end >= len(cleaned_text):
            break

        start = end - overlap

    return chunks

#切割多页文本
def split_pages(
    pages: list[dict[str, int | str]],
    chunk_size: int = 500,
    overlap: int = 50,
) -> list[dict[str, int | str]]:
    """把多页解析结果切成带 page_number 和 chunk_index 的 chunks。"""
    chunks: list[dict[str, int | str]] = []
    chunk_index = 0

    for page in pages:
        page_number = int(page["page_number"])
        text = str(page["text"])

        for content in split_text(text, chunk_size=chunk_size, overlap=overlap):
            chunks.append(
                {
                    "page_number": page_number,
                    "chunk_index": chunk_index,
                    "content": content,
                }
            )
            chunk_index += 1

    return chunks
