# LLM models (GGUF)

The chatbot needs a GGUF model to run. Put **one** model file in one of these folders:

| Folder        | File name   | When used        |
|---------------|-------------|------------------|
| `models/lite/`     | `model.gguf` | Any RAM          |
| `models/standard/` | `model.gguf` | 4+ GB free RAM   |
| `models/advanced/` | `model.gguf` | 8+ GB free RAM   |

**Download a GGUF model** (e.g. from Hugging Face), then rename or copy it to `model.gguf` in the folder that matches your RAM.

Examples:
- **TinyLlama** (small, ~637 MB): search "TinyLlama GGUF" on Hugging Face
- **Phi-2** or **Llama-3.2** in GGUF format also work

Run the app from the project root: `streamlit run app.py`
