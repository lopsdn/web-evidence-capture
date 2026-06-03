import argparse
import json
from pathlib import Path
from typing import Optional

from .capture_http import run_capture
from .config import CaptureConfig, config_from_dict, ensure_run_dirs, init_case, load_config
from .hashing import write_hashes
from .inventory import run_inventory
from .logging_utils import read_json
from .privacy import run_privacy
from .report import generate_report
from .render import run_render
from .singlefile import run_singlefile
from .snapshot import publish_snapshot
from .validate import validate_run
from .wacz import run_wacz


def add_common(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--config", type=Path, help="Path to capture config JSON")
    parser.add_argument("--run-dir", type=Path, help="Existing run directory")
    parser.add_argument("--target-url")
    parser.add_argument("--case-slug")
    parser.add_argument("--allowed-domains", help="Comma-separated allowed hostnames")
    parser.add_argument("--max-pages", type=int)
    parser.add_argument("--cookie-choice", choices=["none", "deny"])
    parser.add_argument("--dry-run", action="store_true")


def resolve_config(args: argparse.Namespace) -> CaptureConfig:
    if args.config:
        config = load_config(args.config)
    else:
        if not args.target_url or not args.case_slug:
            raise SystemExit("--target-url and --case-slug are required when --config is not supplied")
        data = {"target_url": args.target_url, "case_slug": args.case_slug}
        if args.allowed_domains:
            data["allowed_domains"] = [item.strip() for item in args.allowed_domains.split(",") if item.strip()]
        config = config_from_dict(data)
    if args.max_pages is not None:
        config.max_pages = args.max_pages
    if args.cookie_choice is not None:
        config.cookie_choice = args.cookie_choice
    if args.dry_run:
        config.dry_run = True
    return config


def resolve_run_dir(args: argparse.Namespace, config: CaptureConfig, create: bool = False) -> Path:
    if args.run_dir:
        path = args.run_dir
        if create:
            ensure_run_dirs(path)
        return path
    if create:
        return init_case(config)
    metadata_paths = sorted(Path(config.output_root).glob(f"{config.case_slug}/runs/*/manifest/package-metadata.json"))
    if not metadata_paths:
        raise SystemExit("No run directory found; run init-case first or pass --run-dir")
    return metadata_paths[-1].parents[1]


def command_init_case(args: argparse.Namespace) -> None:
    config = resolve_config(args)
    path = init_case(config)
    print(path)


def command_inventory(args: argparse.Namespace) -> None:
    config = resolve_config(args)
    run_dir = resolve_run_dir(args, config)
    run_inventory(config, run_dir)


def command_capture(args: argparse.Namespace) -> None:
    config = resolve_config(args)
    run_dir = resolve_run_dir(args, config)
    run_capture(config, run_dir)


def command_render(args: argparse.Namespace) -> None:
    config = resolve_config(args)
    run_dir = resolve_run_dir(args, config)
    run_render(config, run_dir)


def command_privacy(args: argparse.Namespace) -> None:
    config = resolve_config(args)
    run_dir = resolve_run_dir(args, config)
    run_privacy(config, run_dir)


def command_singlefile(args: argparse.Namespace) -> None:
    config = resolve_config(args)
    run_dir = resolve_run_dir(args, config)
    run_singlefile(config, run_dir)


def command_package_wacz(args: argparse.Namespace) -> None:
    config = resolve_config(args)
    run_dir = resolve_run_dir(args, config)
    run_wacz(config, run_dir)


def command_hash(args: argparse.Namespace) -> None:
    config = resolve_config(args)
    run_dir = resolve_run_dir(args, config)
    rows = write_hashes(run_dir)
    print(json.dumps({"hashed_files": len(rows)}, sort_keys=True))


def command_validate(args: argparse.Namespace) -> None:
    config = resolve_config(args)
    run_dir = resolve_run_dir(args, config)
    result = validate_run(config, run_dir)
    print(json.dumps({"status": result["status"]}, sort_keys=True))


def command_report(args: argparse.Namespace) -> None:
    config = resolve_config(args)
    run_dir = resolve_run_dir(args, config)
    result = generate_report(config, run_dir)
    print(json.dumps(result, sort_keys=True))


def command_snapshot(args: argparse.Namespace) -> None:
    config = resolve_config(args)
    run_dir = resolve_run_dir(args, config)
    result = publish_snapshot(config, run_dir, args.stage, final=args.final)
    print(json.dumps(result, sort_keys=True))


def command_run(args: argparse.Namespace) -> None:
    config = resolve_config(args)
    run_dir = resolve_run_dir(args, config, create=True)
    run_inventory(config, run_dir)
    run_capture(config, run_dir)
    run_render(config, run_dir)
    run_privacy(config, run_dir)
    run_singlefile(config, run_dir)
    run_wacz(config, run_dir)
    validate_run(config, run_dir)
    generate_report(config, run_dir)
    print(run_dir)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="web-evidence", description="Capture and validate public website preservation evidence.")
    subparsers = parser.add_subparsers(dest="command", required=True)
    commands = {
        "init-case": command_init_case,
        "inventory": command_inventory,
        "capture": command_capture,
        "render": command_render,
        "privacy": command_privacy,
        "singlefile": command_singlefile,
        "package-wacz": command_package_wacz,
        "hash": command_hash,
        "validate": command_validate,
        "report": command_report,
        "snapshot": command_snapshot,
        "run": command_run,
    }
    for name, handler in commands.items():
        sub = subparsers.add_parser(name)
        add_common(sub)
        if name == "snapshot":
            sub.add_argument("--stage", required=True)
            sub.add_argument("--final", action="store_true")
        sub.set_defaults(handler=handler)
    return parser


def main(argv: Optional[list] = None) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)
    args.handler(args)


if __name__ == "__main__":
    main()
