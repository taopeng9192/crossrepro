import sys

if "*.md" in sys.argv[1:]:
    print("literal glob received", file=sys.stderr)
    raise SystemExit(2)
print("expanded arguments:", " ".join(sys.argv[1:]))
