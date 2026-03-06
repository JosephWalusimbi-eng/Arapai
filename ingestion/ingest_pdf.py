from pypdf import PdfReader
from sentence_transformers import SentenceTransformer
import faiss, pickle, os
from .chunker import chunk_text

# Support both folder names so PDFs in data/rawpdfs or data/raw_pdfs work
PDF_DIRS = ["data/raw_pdfs", "data/rawpdfs"]
OUT_DIR = "data/embeddings"

model = SentenceTransformer("all-MiniLM-L6-v2")
all_chunks = []

for pdf_dir in PDF_DIRS:
    if not os.path.isdir(pdf_dir):
        continue
    for file in os.listdir(pdf_dir):
        if file.endswith(".pdf"):
            path = os.path.join(pdf_dir, file)
            reader = PdfReader(path)
            for page in reader.pages:
                text = page.extract_text()
                if text:
                    all_chunks.extend(chunk_text(text))

if not all_chunks:
    print("No PDF text found. Put .pdf files in data/raw_pdfs/ or data/rawpdfs/ and run this script again.")
    exit(1)

os.makedirs(OUT_DIR, exist_ok=True)
embeddings = model.encode(all_chunks).astype("float32")

index = faiss.IndexFlatL2(embeddings.shape[1])
index.add(embeddings)

faiss.write_index(index, os.path.join(OUT_DIR, "index.faiss"))

with open(os.path.join(OUT_DIR, "texts.pkl"), "wb") as f:
    pickle.dump(all_chunks, f)

print("PDF ingestion complete.")
