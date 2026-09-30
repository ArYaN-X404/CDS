#!/usr/bin/env python3
"""
Fast Codebase Tool (Universal Symbol & Architecture Navigator)
Created for the Aryan Cognitive Engine to achieve zero-waste token consumption
and sub-second code & architecture discovery on ANY project.
"""

import ast
import os
import re
import sys
from pathlib import Path

# Ensure UTF-8 output on Windows terminals
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

IGNORE_DIRS = {
    '.git', '__pycache__', 'node_modules', 'venv', '.venv', 'env',
    'dist', 'build', '.idea', '.vscode', '.gemini', 'tmp'
}


def get_code_files(root_dir: str):
    code_extensions = {'.py', '.js', '.ts', '.jsx', '.tsx', '.go', '.rs', '.cpp', '.c', '.h'}
    for p in Path(root_dir).rglob('*'):
        if p.is_file() and p.suffix in code_extensions:
            if any(ignored in p.parts for ignored in IGNORE_DIRS):
                continue
            yield p


def find_symbol(root_dir: str, symbol_name: str):
    """Finds all definitions (function, async function, class) of a symbol."""
    matches = []
    symbol_lower = symbol_name.lower()

    for p in get_code_files(root_dir):
        if p.suffix == '.py':
            try:
                with open(p, 'r', encoding='utf-8', errors='ignore') as f:
                    tree = ast.parse(f.read(), filename=str(p))
                for node in ast.walk(tree):
                    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                        if symbol_lower in node.name.lower():
                            matches.append({
                                "file": str(p),
                                "type": type(node).__name__.replace("Def", ""),
                                "name": node.name,
                                "line_start": node.lineno,
                                "line_end": getattr(node, 'end_lineno', node.lineno)
                            })
            except Exception:
                continue
        else:
            # Fallback for JS/TS/Go/Rust using regex
            try:
                with open(p, 'r', encoding='utf-8', errors='ignore') as f:
                    for line_idx, line in enumerate(f, start=1):
                        m = re.search(rf'\b(class|function|async function|fn|def)\s+([A-Za-z0-9_]*{re.escape(symbol_name)}[A-Za-z0-9_]*)', line, re.IGNORECASE)
                        if m:
                            matches.append({
                                "file": str(p),
                                "type": m.group(1),
                                "name": m.group(2),
                                "line_start": line_idx,
                                "line_end": line_idx
                            })
            except Exception:
                continue

    if not matches:
        print(f"❌ Symbol '{symbol_name}' not found in {root_dir}")
        return

    print(f"\n🔍 Found {len(matches)} match(es) for '{symbol_name}':\n")
    print(f"{'Type':<10} | {'Symbol Name':<30} | {'Lines':<12} | {'File Path'}")
    print("-" * 85)
    for m in matches:
        lines_str = f"{m['line_start']}-{m['line_end']}"
        print(f"{m['type']:<10} | {m['name']:<30} | {lines_str:<12} | {m['file']}")


def show_symbol(file_path: str, symbol_name: str):
    """Prints the exact lines of a symbol definition from a specific file."""
    if not os.path.exists(file_path):
        print(f"❌ File not found: {file_path}")
        return

    try:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
            lines = content.splitlines()
    except Exception as e:
        print(f"❌ Error reading {file_path}: {e}")
        return

    if file_path.endswith('.py'):
        try:
            tree = ast.parse(content, filename=file_path)
            target_node = None
            symbol_lower = symbol_name.lower()
            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                    if node.name.lower() == symbol_lower:
                        target_node = node
                        break

            if target_node:
                start = target_node.lineno
                end = getattr(target_node, 'end_lineno', start)
                print(f"\n📄 {file_path} -> {symbol_name} (Lines {start}-{end}):\n" + "=" * 70)
                for idx in range(start - 1, min(end, len(lines))):
                    print(f"{idx + 1:4d}: {lines[idx]}")
                print("=" * 70 + "\n")
                return
        except Exception:
            pass

    # Fallback to line scanning if AST didn't match or non-python
    start = -1
    for idx, line in enumerate(lines):
        if re.search(rf'\b(def|class|function|async def|fn)\s+{re.escape(symbol_name)}\b', line, re.IGNORECASE):
            start = idx
            break

    if start == -1:
        print(f"❌ Symbol '{symbol_name}' not found in {file_path}")
        return

    end = min(start + 40, len(lines))
    print(f"\n📄 {file_path} -> {symbol_name} (Lines {start + 1}-{end}):\n" + "=" * 70)
    for idx in range(start, end):
        print(f"{idx + 1:4d}: {lines[idx]}")
    print("=" * 70 + "\n")


def callers_of(root_dir: str, symbol_name: str):
    """Finds all invocations of a symbol across the project."""
    pattern = re.compile(rf'\b{re.escape(symbol_name)}\s*\(')
    matches = []

    for p in get_code_files(root_dir):
        try:
            with open(p, 'r', encoding='utf-8', errors='ignore') as f:
                for line_num, line in enumerate(f, start=1):
                    if pattern.search(line):
                        matches.append((str(p), line_num, line.strip()))
        except Exception:
            continue

    if not matches:
        print(f"ℹ️ No active callers found for '{symbol_name}()'")
        return

    print(f"\n📞 Found {len(matches)} invocation(s) of '{symbol_name}()':\n")
    for file_path, line_num, line_text in matches:
        print(f"{file_path}:{line_num} -> {line_text}")


def query_architecture(root_dir: str, query: str):
    """Searches architecture documents for a specific topic, returning only relevant sections."""
    doc_patterns = ['*ARCHITECTURE*.md', '*MAP*.md', '*AUDIT*.md', 'README.md']
    found_docs = []
    for pat in doc_patterns:
        for p in Path(root_dir).rglob(pat):
            if any(ignored in p.parts for ignored in IGNORE_DIRS):
                continue
            found_docs.append(p)

    # Deduplicate documents with identical file names
    seen_doc_names = set()
    unique_docs = []
    for d in found_docs:
        if d.name not in seen_doc_names:
            seen_doc_names.add(d.name)
            unique_docs.append(d)
    found_docs = unique_docs

    if not found_docs:
        print(f"❌ No architecture or map files found in {root_dir}")
        return

    query_lower = query.lower()
    matches_found = 0

    print(f"\n🏛️ Architecture Search for '{query}':\n" + "=" * 75)
    for doc in found_docs:
        try:
            with open(doc, 'r', encoding='utf-8', errors='ignore') as f:
                lines = f.readlines()
        except Exception:
            continue

        in_matching_section = False
        section_lines = []
        current_heading = ""
        heading_level = 0

        for idx, line in enumerate(lines):
            line_str = line.strip()
            heading_match = re.match(r'^(#{1,6})\s+(.*)', line_str)

            if heading_match:
                level = len(heading_match.group(1))
                heading_text = heading_match.group(2)

                if in_matching_section:
                    # If we encounter same or higher level heading, close previous match
                    if level <= heading_level:
                        print(f"\n📌 [{doc.name}] {current_heading} (Line {idx + 1 - len(section_lines)}):")
                        print("".join(section_lines[:35]))
                        if len(section_lines) > 35:
                            print(f"   ... [truncated {len(section_lines) - 35} lines]")
                        matches_found += 1
                        in_matching_section = False
                        section_lines = []

                if query_lower in heading_text.lower():
                    in_matching_section = True
                    current_heading = heading_text
                    heading_level = level
                    section_lines = [line]
                    continue

            if in_matching_section:
                section_lines.append(line)
            elif query_lower in line_str.lower() and not heading_match:
                # Direct line match outside a matched heading: grab 3 lines before & 5 after
                start_l = max(0, idx - 2)
                end_l = min(len(lines), idx + 6)
                context = "".join(lines[start_l:end_l])
                print(f"\n📌 [{doc.name}] Context match around line {idx + 1}:")
                print(context)
                matches_found += 1

        if in_matching_section and section_lines:
            print(f"\n📌 [{doc.name}] {current_heading}:")
            print("".join(section_lines[:35]))
            matches_found += 1

    if matches_found == 0:
        print(f"❌ No matching architecture sections found for '{query}'")
    print("=" * 75 + "\n")


def print_tree(root_dir: str, max_depth: int = 2):
    """Prints a lightweight directory tree outline without bloating tokens."""
    print(f"\n📂 Directory Tree for {os.path.abspath(root_dir)} (Depth <= {max_depth}):\n")
    root_path = Path(root_dir).resolve()
    for root, dirs, files in os.walk(root_path):
        # Exclude ignored dirs in-place
        dirs[:] = [d for d in dirs if d not in IGNORE_DIRS]
        rel_path = Path(root).relative_to(root_path)
        depth = len(rel_path.parts)
        if depth > max_depth:
            continue
        indent = "  " * depth
        folder_name = rel_path.name if rel_path.parts else "."
        print(f"{indent}📁 {folder_name}/")
        if depth == max_depth:
            py_count = sum(1 for f in files if f.endswith(('.py', '.js', '.ts', '.md')))
            if py_count > 0:
                print(f"{indent}  └── [{py_count} source/doc files]")
        else:
            for f in files:
                if f.endswith(('.py', '.js', '.ts', '.md', '.json', '.txt', '.env.sample', '.sample')):
                    print(f"{indent}  ├── 📄 {f}")
    print()


def list_symbols_in_file(file_path: str):
    """Lists all classes, functions, and async functions in a specific file."""
    if not os.path.exists(file_path):
        print(f"❌ File not found: {file_path}")
        return
    try:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            tree = ast.parse(f.read(), filename=file_path)
        symbols = []
        for node in ast.iter_child_nodes(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                symbols.append((node.lineno, getattr(node, 'end_lineno', node.lineno), type(node).__name__.replace('Def',''), node.name))
        print(f"\n📑 Symbols in {file_path}:\n" + "-" * 60)
        for start, end, stype, sname in sorted(symbols):
            print(f"{stype:<12} | {sname:<30} | Lines {start}-{end}")
        print("-" * 60 + "\n")
    except Exception as e:
        print(f"❌ Error: {e}")


def slice_symbol(file_path: str, symbol_name: str):
    """
    Outputs the exact slice information and raw code block formatted
    specifically for the Aryan Cognitive Engine's replace_file_content tool.
    Eliminates manual line counting, line drift, and guesswork.
    """
    if not os.path.exists(file_path):
        print(f"❌ File not found: {file_path}")
        return

    try:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
            lines = content.splitlines()
    except Exception as e:
        print(f"❌ Error reading {file_path}: {e}")
        return

    start = -1
    end = -1

    if file_path.endswith('.py'):
        try:
            tree = ast.parse(content, filename=file_path)
            symbol_lower = symbol_name.lower()
            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                    if node.name.lower() == symbol_lower:
                        start = node.lineno
                        end = getattr(node, 'end_lineno', start)
                        break
        except Exception:
            pass

    if start == -1:
        for idx, line in enumerate(lines):
            if re.search(rf'\b(def|class|function|async def|fn)\s+{re.escape(symbol_name)}\b', line, re.IGNORECASE):
                start = idx + 1
                end = min(start + 40, len(lines))
                break

    if start == -1:
        print(f"❌ Symbol '{symbol_name}' not found in {file_path}")
        return

    slice_lines = lines[start - 1:end]
    raw_content = "\n".join(slice_lines)

    abs_path = os.path.abspath(file_path)
    print("\n" + "✂️ " + "=" * 68)
    print("SLICE READY FOR replace_file_content:")
    print(f"TargetFile: {abs_path}")
    print(f"StartLine: {start}")
    print(f"EndLine: {end}")
    print(f"Total Lines: {end - start + 1}")
    print("-" * 70)
    print("--- RAW TARGET CONTENT (Copy exactly) ---")
    print(raw_content)
    print("=" * 70 + "\n")


def run_diagnostic(query: str = ""):
    """
    Instant diagnostic query across local SQLite databases and Supabase Cloud.
    Eliminates writing throwaway scratch Python inspection scripts.
    """
    import sqlite3
    import urllib.request
    import json

    db_candidates = [
        r"ARYAN-TXT2LEECH__V2\cds_assets.db",
        r"R:\ARYAN-TXT2LEECH__V2\cds_assets.db",
        r"cds_assets.db",
        r"R:\cds_assets.db",
        r"File-Sharing-Bot\cds_assets.db",
        r"C:\Users\Aryan\Downloads\EduVault Web\server\database.db",
        r"D:\Projects\EduVault Web\server\database.db"
    ]

    existing_dbs = []
    seen = set()
    for p in db_candidates:
        abs_p = os.path.abspath(p)
        if os.path.exists(abs_p) and abs_p.lower() not in seen:
            seen.add(abs_p.lower())
            existing_dbs.append(abs_p)

    print("\n" + "🩺 " + "=" * 73)
    print("EDUVAULT TELEMETRY & PERSISTENCE DIAGNOSTIC")
    print("=" * 75)

    if not query or query.lower() in ("summary", "status", "all"):
        print("\n📊 Database Inventory & Asset Counts:")
        print(f"{'Status':<8} | {'Rows':<8} | {'Size':<10} | {'Database Location'}")
        print("-" * 75)
        for db in existing_dbs:
            try:
                conn = sqlite3.connect(db)
                c = conn.cursor()
                c.execute("SELECT name FROM sqlite_master WHERE type='table'")
                tables = [r[0] for r in c.fetchall()]
                count_str = "N/A"
                if "video_assets" in tables:
                    c.execute("SELECT count(*) FROM video_assets")
                    count_str = str(c.fetchone()[0])
                elif "assets" in tables:
                    c.execute("SELECT count(*) FROM assets")
                    count_str = str(c.fetchone()[0])
                conn.close()
                sz = f"{os.path.getsize(db) / 1024:.1f} KB"
                print(f"{'✅ OK':<8} | {count_str:<8} | {sz:<10} | {db}")
            except Exception as e:
                print(f"{'⚠️ ERR':<8} | {'-':<8} | {'-':<10} | {db} ({e})")
        print("=" * 75 + "\n")
        return

    # Specific Query: ID, Msg ID, or Title
    print(f"\n🔍 Searching for: '{query}' across SQLite and Supabase...")
    results_found = 0

    for db in existing_dbs:
        try:
            conn = sqlite3.connect(db)
            conn.row_factory = sqlite3.Row
            c = conn.cursor()
            c.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = [r[0] for r in c.fetchall()]
            if "video_assets" in tables:
                c.execute("""
                    SELECT lecture_id, batch_id, quality, tg_message_id, file_id, title, topic
                    FROM video_assets
                    WHERE lecture_id = ? OR tg_message_id = ? OR title LIKE ?
                    LIMIT 5
                """, (str(query), int(query) if str(query).isdigit() else -1, f"%{query}%"))
                rows = c.fetchall()
                if rows:
                    print(f"\n📦 Found in SQLite [{os.path.basename(db)}]:")
                    for r in rows:
                        results_found += 1
                        print(f"  • Lecture ID  : {r['lecture_id']}")
                        print(f"  • Batch ID    : {r['batch_id']}")
                        print(f"  • Title       : {r['title']}")
                        print(f"  • Msg ID      : #{r['tg_message_id']} ({r['quality']})")
                        print(f"  • File ID     : {r['file_id']}")
                        print(f"  • Topic       : {r['topic']}")
            conn.close()
        except Exception:
            pass

    # Supabase REST lookup
    sb_url = os.environ.get("SUPABASE_URL", "https://gjbngruhqsnfiutoahrl.supabase.co").rstrip("/")
    sb_key = os.environ.get("SUPABASE_KEY") or os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "")
    if sb_url and sb_key:
        try:
            filter_param = f"lecture_id=eq.{query}" if str(query).isalnum() else f"title=ilike.*{query}*"
            if str(query).isdigit():
                filter_param = f"or=(lecture_id.eq.{query},tg_message_id.eq.{query})"
            req = urllib.request.Request(
                f"{sb_url}/rest/v1/video_assets?{filter_param}&limit=5",
                headers={
                    "apikey": sb_key,
                    "Authorization": f"Bearer {sb_key}",
                    "User-Agent": "FastCodebaseTool/1.0"
                }
            )
            with urllib.request.urlopen(req, timeout=3) as resp:
                if resp.status == 200:
                    data = json.loads(resp.read().decode('utf-8'))
                    if data:
                        print(f"\n☁️ Found in Supabase Cloud REST:")
                        for r in data:
                            results_found += 1
                            print(f"  • Lecture ID  : {r.get('lecture_id')}")
                            print(f"  • Batch ID    : {r.get('batch_id')}")
                            print(f"  • Title       : {r.get('title')}")
                            print(f"  • Msg ID      : #{r.get('tg_message_id')} ({r.get('quality')})")
                            print(f"  • File ID     : {r.get('file_id')}")
        except Exception as e:
            print(f"ℹ️ Supabase query note: {e}")

    if results_found == 0:
        print(f"❌ No records found matching '{query}'")
    print("\n" + "=" * 75 + "\n")


def sync_drives(direction: str = "d2r"):
    """
    Bidirectionally syncs changed source code between D: and R: drives.
    Avoids slow or complex manual robocopy / PowerShell commands.
    """
    import shutil

    dir_lower = direction.lower()
    if dir_lower in ("d2r", "d"):
        src_root = Path(r"D:\Projects\Content Delivery System (CDS)")
        dst_root = Path(r"R:")
        desc = "D: -> R: (Workspace to RamDisk)"
    elif dir_lower in ("r2d", "r"):
        src_root = Path(r"R:")
        dst_root = Path(r"D:\Projects\Content Delivery System (CDS)")
        desc = "R: -> D: (RamDisk to Workspace)"
    else:
        print(f"❌ Invalid sync direction '{direction}'. Use 'd2r' or 'r2d'.")
        return

    if not src_root.exists():
        print(f"❌ Source directory does not exist: {src_root}")
        return
    if not dst_root.exists():
        print(f"❌ Destination directory does not exist: {dst_root}")
        return

    subdirs_to_sync = [
        "ARYAN-TXT2LEECH__V2",
        "scripts",
        "docs",
        "File-Sharing-Bot"
    ]

    skip_dirs = {
        '.git', '__pycache__', 'venv', '.venv', '.gemini', 'staging', 'downloads',
        'node_modules', 'chrome-profile', 'DawnGraphiteCache', 'GPUPersistentCache', 'Default'
    }
    skip_suffixes = {'.part', '.aria2', '.tmp', '.log', '.crdownload'}

    print(f"\n🔄 Synchronizing: {desc}...")
    copied_count = 0
    total_bytes = 0

    for sub in subdirs_to_sync:
        src_sub = src_root / sub
        if not src_sub.exists():
            continue

        for root, dirs, files in os.walk(src_sub):
            dirs[:] = [d for d in dirs if d not in skip_dirs]
            rel = Path(root).relative_to(src_root)
            dst_dir = dst_root / rel

            for f in files:
                src_file = Path(root) / f
                if src_file.suffix.lower() in skip_suffixes:
                    continue
                # Skip massive binary video files if any strayed
                if src_file.suffix.lower() in {'.mp4', '.mkv', '.ts', '.m4s'}:
                    continue

                dst_file = dst_dir / f

                needs_copy = False
                if not dst_file.exists():
                    needs_copy = True
                else:
                    try:
                        s_stat = src_file.stat()
                        d_stat = dst_file.stat()
                        if s_stat.st_size != d_stat.st_size or s_stat.st_mtime > (d_stat.st_mtime + 1):
                            needs_copy = True
                    except Exception:
                        needs_copy = True

                if needs_copy:
                    try:
                        dst_dir.mkdir(parents=True, exist_ok=True)
                        shutil.copy2(src_file, dst_file)
                        copied_count += 1
                        total_bytes += src_file.stat().st_size
                    except Exception as e:
                        print(f"⚠️ Error copying {src_file.name}: {e}")

    # Also sync root fast_codebase_tool.py and mirror scripts folder into ARYAN-TXT2LEECH__V2/scripts
    root_script = src_root / "scripts" / "fast_codebase_tool.py"
    r_root_script = dst_root / "scripts" / "fast_codebase_tool.py"
    if root_script.exists():
        try:
            r_root_script.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(root_script, r_root_script)
        except Exception:
            pass

    src_scripts = src_root / "scripts"
    dst_inner_scripts = dst_root / "ARYAN-TXT2LEECH__V2" / "scripts"
    if src_scripts.exists():
        try:
            dst_inner_scripts.mkdir(parents=True, exist_ok=True)
            for sf in src_scripts.glob("*.py"):
                shutil.copy2(sf, dst_inner_scripts / sf.name)
        except Exception:
            pass

    kb = total_bytes / 1024
    print(f"⚡ Sync complete! {copied_count} file(s) synchronized ({kb:.1f} KB).")
    print("=" * 75 + "\n")


def run_checks(test_target: str = ""):
    """
    Runs pytest synchronously with minimal token output.
    Ensures sub-2-second fast fail without background task transitions.
    """
    import subprocess

    if not test_target:
        if os.path.exists(r"ARYAN-TXT2LEECH__V2\tests\test_resume_and_pipeline.py"):
            test_target = r"ARYAN-TXT2LEECH__V2\tests\test_resume_and_pipeline.py"
        elif os.path.exists("tests"):
            test_target = "tests"
        else:
            test_target = "."

    print(f"\n🧪 Running verification: pytest {test_target} -q --tb=short\n" + "-" * 70)
    cmd = [sys.executable, "-m", "pytest", test_target, "-q", "--tb=short"]
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        output = (proc.stdout + "\n" + proc.stderr).strip()
        lines = [line for line in output.splitlines() if not line.startswith("warnings summary") and "Warning" not in line]
        concise = "\n".join(lines[-15:]) if len(lines) > 15 else "\n".join(lines)
        print(concise)
        if proc.returncode == 0:
            print("-" * 70)
            print("✅ All dynamic verification tests PASSED!\n")
        else:
            print("-" * 70)
            print(f"❌ Test run FAILED with exit code {proc.returncode}\n")
    except subprocess.TimeoutExpired:
        print("❌ Test execution timed out (> 30s)!\n")
    except Exception as e:
        print(f"❌ Test runner error: {e}\n")


def main():
    if len(sys.argv) < 2:
        print("Usage:")
        print("  fast_codebase_tool.py arch <topic_or_keyword>   (Query architecture & audit docs surgically)")
        print("  fast_codebase_tool.py find <symbol>             (Find class/func definitions across repo)")
        print("  fast_codebase_tool.py symbols <file>            (List all symbols in a file)")
        print("  fast_codebase_tool.py show <file> <symbol>      (Print exact code lines of symbol)")
        print("  fast_codebase_tool.py slice <file> <symbol>     (Get exact lines & snippet for replace_file_content)")
        print("  fast_codebase_tool.py callers <symbol>          (Find all callers of a function)")
        print("  fast_codebase_tool.py diag [query]              (Diagnostic inspection of local SQLite & Supabase)")
        print("  fast_codebase_tool.py sync [d2r|r2d]            (Bidirectional sync between D: and R: drives)")
        print("  fast_codebase_tool.py check [test_target]       (Fast synchronous pytest verification)")
        print("  fast_codebase_tool.py tree [depth]              (Print lightweight project tree)")
        sys.exit(1)

    cmd = sys.argv[1].lower()

    if cmd == "arch":
        if len(sys.argv) < 3:
            print("Usage: fast_codebase_tool.py arch <topic>")
            sys.exit(1)
        query_architecture(".", " ".join(sys.argv[2:]))

    elif cmd == "find":
        if len(sys.argv) < 3:
            print("Usage: fast_codebase_tool.py find <symbol>")
            sys.exit(1)
        find_symbol(".", sys.argv[2])

    elif cmd == "symbols":
        if len(sys.argv) < 3:
            print("Usage: fast_codebase_tool.py symbols <file>")
            sys.exit(1)
        list_symbols_in_file(sys.argv[2])

    elif cmd == "show":
        if len(sys.argv) < 4:
            print("Usage: fast_codebase_tool.py show <file> <symbol>")
            sys.exit(1)
        show_symbol(sys.argv[2], sys.argv[3])

    elif cmd == "slice":
        if len(sys.argv) < 4:
            print("Usage: fast_codebase_tool.py slice <file> <symbol>")
            sys.exit(1)
        slice_symbol(sys.argv[2], sys.argv[3])

    elif cmd == "callers":
        if len(sys.argv) < 3:
            print("Usage: fast_codebase_tool.py callers <symbol>")
            sys.exit(1)
        callers_of(".", sys.argv[2])

    elif cmd == "diag":
        query = " ".join(sys.argv[2:]) if len(sys.argv) > 2 else ""
        run_diagnostic(query)

    elif cmd == "sync":
        direction = sys.argv[2] if len(sys.argv) > 2 else "d2r"
        sync_drives(direction)

    elif cmd == "check":
        target = sys.argv[2] if len(sys.argv) > 2 else ""
        run_checks(target)

    elif cmd == "tree":
        depth = int(sys.argv[2]) if len(sys.argv) > 2 else 2
        print_tree(".", depth)

    else:
        print(f"Unknown command: {cmd}")


if __name__ == "__main__":
    main()
