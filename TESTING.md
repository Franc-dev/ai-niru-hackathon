# Testing the Agentic Tools

## Changes Made

### 1. Fixed Resource Response Format
- Added `🔗 {url}` to resource responses so frontend can extract URLs
- Updated frontend regex to parse `🔗` URLs properly

### 2. Enhanced Intent Detection Keywords

**Crisis Keywords:**
- Added: "crisis help", "need crisis", "emergency", "nataka mkubwa"

**Counselor Keywords:**
- Added: "find a", "tafuta", "professional"

**Resource Keywords:**
- Added: "videos", "show me", "nyesha", "resource"

### 3. Increased RAG Threshold
- Changed from `0.15` to `0.35` to prevent RAG from catching tool-specific queries
- This ensures counselor/resource/crisis tools trigger first

### 4. Added Debug Logging
- Process message flow now prints:
  - User message and detected language
  - Crisis detection result
  - Intents detected
  - Tools triggered and results found

## To Test

1. **Start the server:**
   ```bash
   training_env/Scripts/python.exe training/scripts/4_serve_sklearn_rag.py
   ```

2. **Run simple tests:**
   ```bash
   python test_tools_simple.py
   ```

3. **Test in the UI:**
   - Crisis: "I need crisis help" → Should show hotline
   - Counselors: "Find a counselor" → Should show counselor cards
   - Resources: "Show me videos" → Should show video cards with thumbnails

## Expected Results

- **Crisis Detection:** Returns hotline number immediately
- **Find Counselor:** Shows 3-5 counselor cards with names, ratings, specializations
- **Get Resources:** Shows 5 video/article cards with thumbnails (for YouTube)
- **RAG Fallback:** Only triggers when no specific tool intent detected AND score > 0.35

## Server Logs to Watch

Look for debug output like:
```
[DEBUG] User message: Find a counselor
[DEBUG] Language: en
[DEBUG] Crisis detected: False
[DEBUG] Intents: {'find_counselor': True, ...}
[DEBUG] Looking for counselors...
[DEBUG] Found 3 counselors
```
