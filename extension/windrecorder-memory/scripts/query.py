"""JSON command-line adapter for Windrecorder's read-only query service."""

import argparse
import json
import sys
from pathlib import Path

sys.dont_write_bytecode = True


def parser():
    result = argparse.ArgumentParser(description=__doc__)
    result.add_argument("--root", required=True, help="Actual Windrecorder installation containing user data")
    commands = result.add_subparsers(dest="command", required=True)
    commands.add_parser("status", help="Installation, record bounds, count and available capabilities")
    for name in ("search", "context", "record", "counts", "notes"):
        command = commands.add_parser(name)
        if name in {"search", "counts", "notes"}:
            command.add_argument("--start", required=True, help="Inclusive local ISO date/time")
            command.add_argument("--end", required=True, help="Exclusive local ISO date/time")
        if name in {"search", "notes"}:
            command.add_argument("--query", default="")
        if name == "search":
            command.add_argument("--exclude", default="")
        if name == "context":
            command.add_argument("--at", required=True, help="Local ISO date/time at the center")
            command.add_argument("--seconds", type=int, default=300, help="Radius on each side, at most 86400")
        if name == "record":
            command.add_argument("--id", required=True, help="record_id from an earlier search")
            command.add_argument("--text-offset", type=int, default=0)
        if name == "counts":
            command.add_argument("--by", choices=("hour", "day", "month"), default="day")
        else:
            command.add_argument("--text-limit", type=int, default=2000)
            if name != "record":
                command.add_argument("--limit", type=int, default=20)
                command.add_argument("--offset", type=int, default=0)
    return result


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    args = parser().parse_args()
    try:
        root = Path(args.root).resolve(strict=True)
        # In-repo use can inspect another installation; copied skills use that
        # installation's updated query API. Neither path imports the app bootstrap.
        candidates = (Path(__file__).resolve().parents[3], root)
        source = next((path for path in candidates if (path / "windrecorder/query_service.py").is_file()), None)
        if source is None:
            raise ValueError("Windrecorder query_service.py is missing; update this installation to the skill-enabled version")
        sys.path.insert(0, str(source))
        from windrecorder.query_service import RecordQuery, parse_datetime

        service = RecordQuery(root)
        if args.command == "status":
            output = service.status()
        elif args.command == "record":
            output = service.record(args.id, text_limit=args.text_limit, text_offset=args.text_offset)
        elif args.command == "counts":
            output = service.counts(parse_datetime(args.start), parse_datetime(args.end), args.by)
        else:
            options = dict(limit=args.limit, offset=args.offset, text_limit=args.text_limit)
            if args.command == "context":
                output = service.context(parse_datetime(args.at), args.seconds, **options)
            else:
                if args.command == "search":
                    options["exclude"] = args.exclude
                output = getattr(service, args.command)(
                    parse_datetime(args.start), parse_datetime(args.end), args.query, **options
                )
        print(json.dumps(dict(ok=True, command=args.command, root=str(root), result=output), ensure_ascii=False))
        return 0
    except (OSError, ValueError, KeyError, TypeError, OverflowError) as error:
        print(json.dumps(dict(ok=False, command=args.command, error=str(error)), ensure_ascii=False))
        return 2
    except Exception as error:
        # SQLite errors must not masquerade as an empty result. Avoid data-bearing traces.
        print(json.dumps(dict(ok=False, command=args.command, error=f"{type(error).__name__}: {error}"), ensure_ascii=False))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
