from pypdf import PdfReader
from sentence_transformers import SentenceTransformer
import faiss, pickle, os
from chunker import chunk_text

PDF_DIR = "data/raw_pdfs/"
OUT_DIR = "data/embeddings/"

model = SentenceTransformer("all-MiniLM-L6-v2")
all_chunks = []

for file in os.listdir(PDF_DIR):
    if file.endswith(".pdf"):
        reader = PdfReader(os.path.join(PDF_DIR, file))
        for page in reader.pages:
            text = page.extract_text()
            if text:
                all_chunks.extend(chunk_text(text))

embeddings = model.encode(all_chunks).astype("float32")

index = faiss.IndexFlatL2(embeddings.shape[1])
index.add(embeddings)

faiss.write_index(index, os.path.join(OUT_DIR, "index.faiss"))

with open(os.path.join(OUT_DIR, "texts.pkl"), "wb") as f:
    pickle.dump(all_chunks, f)

print("PDF ingestion complete.")
