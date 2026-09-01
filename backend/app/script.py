import os
import re

files_to_process = [
    r"agents\pipeline.py",
    r"agents\tutor.py",
    r"services\deck_service.py",
    r"services\embedding_service.py",
    r"services\knowledge\hybrid_search.py",
    r"services\knowledge\ppt_processor.py",
    r"services\knowledge\youtube_processor.py",
    r"services\llm_service.py",
    r"services\ppt_renderer.py",
    r"services\presentation\cache.py",
    r"services\presentation\orchestrator.py",
    r"services\presentation\qa_agent.py",
    r"services\presentation\visual_agent.py",
    r"services\presentation_engine\builder.py",
    r"services\presentation_engine\layout_engine.py",
    r"services\quiz\generator.py",
    r"services\teach\exports.py",
    r"services\teach\tools.py",
    r"services\vector_service.py",
    r"services\video\audio\audio_timeline.py",
    r"services\video\orchestrator.py",
    r"services\video\planner.py",
    r"services\video\stock\stock_service.py",
    r"services\video\tts\tts_service.py",
    r"services\web_search.py"
]

import_statement = "from app.core.logging import logger\n"

for relative_path in files_to_process:
    filepath = os.path.join(r"c:\Users\kaust\Desktop\Stuff\VS Code\AISTUDYASSISANT\backend\app", relative_path)
    if not os.path.exists(filepath):
        print(f"Skipping {filepath} (does not exist)")
        continue
        
    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()
        
    # Check if print exists
    if "print(" not in content:
        continue
        
    # Check if we need to add import
    needs_import = False
    if "from app.core.logging import logger" not in content:
        needs_import = True
        
    # Replace print( -> logger.info(
    # A bit naive but works for the current codebase as seen from grep
    # We will use regex to determine log level based on contents
    def repl(m):
        prefix = m.group(1)
        inner = m.group(2)
        if "error" in inner.lower() or "failed" in inner.lower() or "exception" in inner.lower():
            return f"{prefix}logger.error({inner}"
        elif "warn" in inner.lower():
            return f"{prefix}logger.warning({inner}"
        else:
            return f"{prefix}logger.info({inner}"
            
    new_content = re.sub(r'([ \t]*)print\((.*)', repl, content)
    
    if needs_import:
        # insert after first docstring or other imports
        lines = new_content.split('\n')
        insert_idx = 0
        for i, line in enumerate(lines):
            if line.startswith('import ') or line.startswith('from '):
                insert_idx = i
                break
        
        if insert_idx == 0:
            for i, line in enumerate(lines):
                if not line.startswith('\"\"\"') and not line.startswith('\'\'\'') and line.strip():
                    insert_idx = i
                    break
                    
        lines.insert(insert_idx, import_statement.strip())
        new_content = '\n'.join(lines)
        
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(new_content)
        
    print(f"Updated {filepath}")
