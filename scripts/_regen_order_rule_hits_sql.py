"""Regenerate master.order_rule_hits INSERT in schema.sql from data_csv."""
import csv
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
schema = ROOT / "init_scripts" / "ecommerce_fraud" / "schema.sql"
csv_path = ROOT / "data_csv" / "order_rule_hits.csv"

text = schema.read_text(encoding="utf-8")
start = text.index("INSERT INTO master.order_rule_hits")
marker = "pg_get_serial_sequence('master.order_rule_hits'"
idx = text.index(marker, start)
end = text.index(");", idx) + 2
while end < len(text) and text[end] in "\r\n":
    end += 1


def esc(s: str) -> str:
    return s.replace("'", "''")


rows: list[str] = []
with csv_path.open(encoding="cp1252", newline="") as f:
    for r in csv.DictReader(f):
        rows.append(
            "    ({hit_id}, '{oid}', '{rid}', '{rname}', '{desc}', '{ts}')".format(
                hit_id=r["hit_id"],
                oid=esc(r["order_id"]),
                rid=esc(r["rule_id"]),
                rname=esc(r["rule_name"]),
                desc=esc(r["rule_description"]),
                ts=esc(r["created_at"]),
            )
        )

block = (
    "INSERT INTO master.order_rule_hits "
    "(hit_id, order_id, rule_id, rule_name, rule_description, created_at)\n"
    "VALUES\n"
    + ",\n".join(rows)
    + "\nON CONFLICT (hit_id) DO NOTHING;\n\n"
    "SELECT setval(\n"
    "    pg_get_serial_sequence('master.order_rule_hits', 'hit_id'),\n"
    "    COALESCE((SELECT MAX(hit_id) FROM master.order_rule_hits), 1)\n"
    ");\n"
)

odd = 0
for n, line in enumerate(block.splitlines(), 1):
    if line.replace("''", "").count("'") % 2 == 1:
        odd += 1
        print("odd", n, line[:120])

if odd:
    raise SystemExit(f"abort: {odd} lines with unbalanced quotes")

new_text = text[:start] + block + text[end:]
schema.write_text(new_text, encoding="utf-8", newline="\n")
print(f"wrote {len(rows)} hit rows into {schema}")
print("file lines:", new_text.count("\n") + 1)
