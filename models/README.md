# LLM models (GGUF)

The chatbot needs a GGUF model to run. Put **one** model file in one of these folders:

| Folder            | File name   | When used      |
|-------------------|-------------|----------------|
| `models/lite/`    | `model.gguf` | Any RAM        |
| `models/standard/`| `model.gguf` | 4+ GB free RAM |
| `models/advanced/`| `model.gguf` | 8+ GB free RAM |

## Use quantized models (Q4_K_M / Q5_K_M)

**Prefer Q4_K_M or Q5_K_M** GGUF variants: they are smaller and faster with little quality loss. Download one of the following, then **rename or copy** the file to `model.gguf` in the folder that matches your RAM.

### Lite (any RAM, ~600 MB)

- **TinyLlama 1.1B Chat, Q4_K_M**  
  https://huggingface.co/TheBloke/TinyLlama-1.1B-Chat-v1.0-GGUF/resolve/main/tinyllama-1.1b-chat-v1.0.Q4_K_M.gguf  
  → Save as `models/lite/model.gguf`

### Standard (4+ GB free RAM)

- **Llama-2 7B Chat, Q4_K_M** (works with pinned `llama-cpp-python==0.2.20`)  
  https://huggingface.co/TheBloke/Llama-2-7B-Chat-GGUF/resolve/main/llama-2-7b-chat.Q4_K_M.gguf  
  → Save as `models/standard/model.gguf`

> Note: Qwen2.5 GGUF uses the `qwen2` architecture and can fail with older pinned llama.cpp builds.

### Advanced (8+ GB free RAM)

- **Mistral 7B Instruct v0.2, Q4_K_M**  
  https://huggingface.co/TheBloke/Mistral-7B-Instruct-v0.2-GGUF/resolve/main/mistral-7b-instruct-v0.2.Q4_K_M.gguf  
  → Save as `models/advanced/model.gguf`

---

**Summary:** Prefer **Q4_K_M** (or **Q5_K_M**) over larger quants; they run faster and use less RAM. Run the app from the project root: `streamlit run app.py`
