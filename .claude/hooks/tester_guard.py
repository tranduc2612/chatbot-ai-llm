"""PreToolUse guard cho subagent `api-tester`.

Chặn (exit 2) mọi lệnh Bash:
  1. liên quan tới GitHub / git (git, gh, github.com, githubusercontent...)
  2. đọc / tìm / liệt kê mã nguồn hoặc file cấu hình của dự án

Đây là lớp chặn "best effort" theo mẫu lệnh; agent còn bị giới hạn bởi danh
sách tools (chỉ có Bash) và chỉ dẫn trong system prompt.
"""

import json
import re
import sys

# --- 1. GitHub / git -------------------------------------------------------
GITHUB_PATTERNS = [
    r"(^|[\s;&|(`$])git(\s|$)",          # lệnh git
    r"(^|[\s;&|(`$])gh(\s|$)",           # GitHub CLI
    r"github",                           # github.com, api.github.com, raw.githubusercontent.com...
    r"\.git([/\\\s'\"]|$)",              # thư mục .git
]

# --- 2. Đọc mã nguồn -------------------------------------------------------
# Thư mục / file của dự án không được đụng tới
PROJECT_PATHS = [
    r"backend",
    r"frontend",
    r"migrations",
    r"\.claude",
    r"CLAUDE\.md",
    r"\.env",
    r"alembic\.ini",
    r"pyproject\.toml",
    r"uv\.lock",
]

# Phần mở rộng file mã nguồn / cấu hình
CODE_EXT = r"\.(py|pyi|js|jsx|ts|tsx|mjs|cjs|html|css|ini|toml|lock|cfg|yaml|yml|md|sql|mako|env)\b"

# Lệnh dùng để đọc / tìm / liệt kê file
READ_CMDS = [
    "cat", "head", "tail", "less", "more", "bat", "nl", "tac", "sed", "awk",
    "grep", "egrep", "fgrep", "rg", "ag", "ack", "find", "fd", "ls", "dir", "tree",
    "strings", "xxd", "od", "hexdump", "cp", "mv", "tar", "zip", "base64", "diff",
    "type", "get-content", "gc", "select-string", "get-childitem", "gci",
    "code", "vim", "vi", "nano", "notepad", "open", "start", "explorer",
]
READ_CMD_RE = r"(^|[\s;&|(`$])(" + "|".join(re.escape(c) for c in READ_CMDS) + r")(\s|$)"

# Đọc file qua ngôn ngữ lập trình (python -c "open(...)", node fs.readFile...)
CODE_READ_API = [
    r"\bopen\s*\(",
    r"read_text\s*\(",
    r"read_bytes\s*\(",
    r"readFile",
    r"\bos\.walk\b",
    r"\bos\.listdir\b",
    r"\bglob\b",
    r"\bscandir\b",
    r"\binspect\b",
    r"__file__",
    r"importlib",
]

# Lệnh khởi động server được phép (dù có cd vào backend)
SERVER_START_RE = r"^\s*cd\s+[\"']?[^;&|]*backend[\"']?\s*(&&|;)\s*uv\s+run\s+(uvicorn\s+main:app|fastapi\s+(dev|run)\s+main\.py)[^;&|<>]*$"


def deny(reason: str) -> None:
    print(f"[tester_guard] Bị chặn: {reason}. Agent này chỉ được test qua HTTP "
          f"(black-box), không được vào GitHub hay đọc mã nguồn.", file=sys.stderr)
    sys.exit(2)


def check_bash(cmd: str) -> None:
    low = cmd.lower()

    for pat in GITHUB_PATTERNS:
        if re.search(pat, low):
            deny("lệnh liên quan tới git/GitHub")

    # Cho phép đúng một dạng: khởi động server
    if re.match(SERVER_START_RE, cmd, re.IGNORECASE):
        return

    touches_project = any(re.search(p, cmd, re.IGNORECASE) for p in PROJECT_PATHS)
    touches_code = re.search(CODE_EXT, low) is not None
    reads = re.search(READ_CMD_RE, low) is not None
    api_reads = any(re.search(p, cmd) for p in CODE_READ_API)

    if touches_project:
        deny("lệnh tham chiếu tới thư mục/file mã nguồn của dự án")
    if reads and touches_code:
        deny("đọc/tìm file mã nguồn hoặc cấu hình")
    if api_reads:
        deny("đọc file/thư mục bằng code (open, readFile, os.walk, glob...)")
    # Agent không cần di chuyển thư mục
    if re.search(r"(^|[\s;&|(])(cd|pushd|set-location|sl|chdir)(\s|$)", low):
        deny("chuyển thư mục (chỉ được cd khi khởi động server)")
    # Lệnh đọc file chỉ được dùng để lọc output sau pipe, không được mở file
    file_readers = ["cat", "head", "tail", "less", "more", "bat", "nl", "tac", "sed",
                    "awk", "strings", "xxd", "od", "hexdump", "base64", "type",
                    "get-content", "gc", "diff", "cp", "mv", "tar", "zip"]
    fr = "|".join(re.escape(c) for c in file_readers)
    for m in re.finditer(r"(^|[\s;&|(`$])(" + fr + r")(\s|$)", low):
        before = low[:m.start(2)].rstrip()
        if not before.endswith("|") or before.endswith("||"):
            deny(f"dùng '{m.group(2)}' để đọc/sao chép file (chỉ được dùng sau pipe)")
    # Tìm kiếm đệ quy (grep -r, rg, ag...) = dò mã nguồn; grep sau pipe vẫn được
    if re.search(r"(^|[\s;&|(])(e|f)?grep\s+[^|]*(-[a-z]*r|--recursive|-[a-z]*d\s*recurse)", low):
        deny("tìm kiếm đệ quy trong file")
    if re.search(r"(^|[;&(]|&&)\s*(rg|ag|ack|select-string)(\s|$)", low):
        deny("tìm kiếm trong file")
    # Lệnh đọc với wildcard (cat *, head src/*...)
    if reads and re.search(r"(^|[\s/\\])[^\s|'\"]*\*", cmd):
        deny("đọc file bằng wildcard")
    # ls / find / tree không đối số trong thư mục dự án cũng là dò mã nguồn
    if re.search(r"(^|[\s;&|])(ls|dir|tree|find|fd|get-childitem|gci)(\s|$)", low):
        deny("liệt kê file trong dự án")


def main() -> None:
    try:
        data = json.load(sys.stdin)
    except Exception:
        deny("không đọc được input của hook")
        return

    tool = data.get("tool_name", "")
    tool_input = data.get("tool_input", {}) or {}

    if tool in ("Bash", "PowerShell"):
        check_bash(str(tool_input.get("command", "")))
    elif tool in ("Read", "Grep", "Glob", "Edit", "Write", "NotebookEdit",
                  "WebFetch", "WebSearch") or tool.startswith("mcp__"):
        # Phòng khi ai đó lỡ thêm tool này vào agent
        deny(f"tool {tool} không được phép cho agent test")

    sys.exit(0)


if __name__ == "__main__":
    main()
