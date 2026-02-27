# Maker Studio: Complete Setup & Execution Guide (v2.0)

This guide provides the definitive steps to run the Hybrid n8n + Python system using the updated free image engine and modern n8n v2.x nodes.

---

## 🚀 Step 1: Python environment & Storage

Ensure your directory structure is initialized for the hand-off.

1.  **Check Folders**: Verify you have `jobs/` and `assets/` folders in your root.
2.  **Environment**: Your `.env` should have absolute paths for `ASSETS_DIR`, `JOBS_DIR`, and your `GROQ_API_KEY`.
3.  **No Image API Needed**: You can leave the Gemini key blank for images, as we now use the free **Pollinations.ai** service.
4.  **FFmpeg (CRITICAL)**: You must have FFmpeg installed on your computer.
    - Download from [ffmpeg.org](https://ffmpeg.org/download.html).
    - **Verify**: Open a terminal and type `ffmpeg -version`. If it says "not recognized", you must add the FFmpeg `bin` folder to your **Windows System PATH**.

## 🤖 Step 2: Modern n8n Workflow Setup (v2.4.8+)

This is the "Brain" that triggers the Python engine.

### A. The "Extract From File" Node (JSON Parsing)

1.  **Read Sample Feed**: Set this to read `sample_topics.json`.
2.  **Add "Extract From File"**: Connect it to the Read node.
    - **Operation**: `Extract from JSON`
    - **Source Key** (or Binary Property): Type **`data`**
    - **Split Into Items**: Toggle this **ON** (This removes the extra `data` layer and fixes the variable resolution).
    - **Verify**: In the node’s **Output** tab, you should see `topic` directly at the top level, not inside an array.

### B. The "Run Maker Engine" Node (Execution)

1.  **Add "Execute Command"**: Connect it to the Extract node.
2.  **Expression Mode**: Above the Command box, click the **Expression** tab.
3.  **The Command**: Paste this exactly (it handles the nesting from the JSON file):
    ```bash
    c:\Users\RAPH-EXT\maker\venv\Scripts\python.exe c:\Users\RAPH-EXT\maker\maker_studio.py --topic "{{ $json.data[0].topic }}" --category "{{ $json.data[0].category }}" --json --produce
    ```

## 🔍 Step 3: Troubleshooting Errors

I have updated the engine to be "n8n friendly".

- **Green Node, but Error message**: If the "Run Maker Engine" node turns green but you see a JSON message like `{"status": "Error", "message": "..."}`, read the message! It will tell you if FFmpeg is missing or if an API key is wrong.
- **Red Node (Command Failed)**: If the node turns red, it usually means there is a syntax error in your command or the Python environment is broken. Double-check your paths!
- **RESTART**: If you just installed FFmpeg or changed your `.env` file, you **MUST restart the terminal** where n8n is running.

## 📊 Step 4: MongoDB Integration (Optional)

To track your jobs in the cloud:

1.  Add a **MongoDB Node** to the start of your n8n workflow.
2.  Use the `MONGODB_URI` from your `.env`.
3.  Choose **Action**: `Insert` and **Collection**: `job_queue`.
4.  Set **Status**: `Pending`.

## 🎬 Step 5: Running your first job

1.  In n8n, click **Execute Workflow**.
2.  **Watch the logs**:
    - If you see `Connected to MongoDB Atlas`, your DB is linked.
    - If you see `Free image gen: 200`, your Pollinations image is downloaded.
3.  **Check Output**: Your finished video will be in `assets/renders/The_Rise_of_the_Ottoman_Empire.mp4`.

---

### 🛠️ Troubleshooting

- **Variables still look like `{{...}}`?** You missed Step 2B (Toggle "Expression" tab).
- **Date/Time output?** You missed Step 2A (Add "Extract From File" node).
- **DNS Timeout?** Use Google DNS (8.8.8.8) on your Windows machine.
