import argparse
import socket
import sys
from pathlib import Path


def _migrate() -> None:
    from alembic import command
    from alembic.config import Config

    from .config import get_settings

    root = Path(__file__).resolve().parents[2]
    cfg = Config(str(root / "alembic.ini"))
    cfg.set_main_option("script_location", str(root / "migrations"))
    cfg.set_main_option("sqlalchemy.url", get_settings().database_url)
    command.upgrade(cfg, "head")


def _lan_ip() -> str | None:
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(("10.255.255.255", 1))
            return s.getsockname()[0]
    except OSError:
        return None


def cmd_serve(args: argparse.Namespace) -> None:
    import uvicorn

    _migrate()
    ip = _lan_ip()
    print(f"GigaLegs on http://localhost:{args.port}", flush=True)
    if args.host == "0.0.0.0" and ip:
        print(
            f"On your phone (same Wi-Fi): http://{ip}:{args.port}  or  "
            f"http://{socket.gethostname().removesuffix('.local')}.local:{args.port}",
            flush=True,
        )
    uvicorn.run("gigalegs.web.app:app", host=args.host, port=args.port, reload=args.reload)


def cmd_log(args: argparse.Namespace) -> None:
    from . import services as S
    from .db import LOCAL_USER_ID, get_sessionmaker
    from .engine.shorthand import parse

    text = args.text if args.text != "-" else sys.stdin.read()
    r = parse(text, S.today())
    for line, msg in r.errors:
        print(f"line {line}: {msg}", file=sys.stderr)
    if r.errors:
        sys.exit(1)
    if not args.save:
        print(
            f"OK: {len(r.lifts)} lift block(s), {sum(len(x.sets) for x in r.lifts)} sets, "
            f"{len(r.rides)} ride(s), {len(r.metrics)} metric(s). Add --save to log it."
        )
        return
    _migrate()
    with get_sessionmaker()() as db:
        S.ensure_user(db, LOCAL_USER_ID)
        for line in S.save_parsed(db, LOCAL_USER_ID, r):
            print(line)


def cmd_export(args: argparse.Namespace) -> None:
    from . import services as S
    from .config import get_settings
    from .db import LOCAL_USER_ID, get_sessionmaker

    _migrate()
    out = Path(args.out) if args.out else get_settings().root / "data" / "logs"
    with get_sessionmaker()() as db:
        S.ensure_user(db, LOCAL_USER_ID)
        for name, n in S.export_jsonl(db, LOCAL_USER_ID, out).items():
            print(f"{out / name}: {n} rows")


def main() -> None:
    ap = argparse.ArgumentParser(prog="gigalegs")
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("serve", help="run the web app")
    s.add_argument("--host", default="0.0.0.0")
    s.add_argument("--port", type=int, default=8000)
    s.add_argument("--reload", action="store_true")
    s.set_defaults(fn=cmd_serve)
    lg = sub.add_parser("log", help="parse (and with --save, log) shorthand; '-' reads stdin")
    lg.add_argument("text")
    lg.add_argument("--save", action="store_true")
    lg.set_defaults(fn=cmd_log)
    ex = sub.add_parser("export", help="write data/logs/*.jsonl for Claude")
    ex.add_argument("--out")
    ex.set_defaults(fn=cmd_export)
    m = sub.add_parser("migrate", help="apply DB migrations")
    m.set_defaults(fn=lambda a: _migrate())
    args = ap.parse_args()
    args.fn(args)


if __name__ == "__main__":
    main()
