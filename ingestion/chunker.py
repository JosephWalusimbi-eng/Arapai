def chunk_text(text, chunk_size=500, overlap=50):
    if not text or chunk_size <= 0:
        return []
    chunks = []
    start = 0
    while start < len(text):
        end = min(start + chunk_size, len(text))
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)
        start = end - overlap if overlap < end - start else end
    return chunks
