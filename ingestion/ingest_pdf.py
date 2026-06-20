from pypdf import PdfReader
from sentence_transformers import SentenceTransformer
import faiss
import pickle
import os
from ingestion.chunker import chunk_text

# Support both folder names (app message mentions raw_pdfs and rawpdfs)
PDF_DIRS = ["data/raw_pdfs", "data/rawpdfs"]
OUT_DIR = "data/embeddings"

os.makedirs(OUT_DIR, exist_ok=True)

model = SentenceTransformer("all-MiniLM-L6-v2")
all_chunks = []

for pdf_dir in PDF_DIRS:
    if not os.path.isdir(pdf_dir):
        continue
    for file in sorted(os.listdir(pdf_dir)):
        if not file.lower().endswith(".pdf"):
            continue
        path = os.path.join(pdf_dir, file)
        try:
            reader = PdfReader(path)
            for page in reader.pages:
                text = page.extract_text()
                if text:
                    all_chunks.extend(chunk_text(text))
        except Exception as e:
            print(f"Warning: skipped {path}: {e}")

if not all_chunks:
    print("No text chunks from PDFs. Add PDFs to data/raw_pdfs or data/rawpdfs and run again.")
    raise SystemExit(1)

embeddings = model.encode(all_chunks).astype("float32")
index = faiss.IndexFlatL2(embeddings.shape[1])
index.add(embeddings)

faiss.write_index(index, os.path.join(OUT_DIR, "index.faiss"))
with open(os.path.join(OUT_DIR, "texts.pkl"), "wb") as f:
    pickle.dump(all_chunks, f)

print("PDF ingestion complete.")
