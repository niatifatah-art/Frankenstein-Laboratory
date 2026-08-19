from __future__ import annotations

import argparse
import json

from .product import MODEL_FAMILY, PRODUCT_NAME, PRODUCT_TAGLINE, model_profile, product_manifest


def _human_family() -> str:
    lines = [f"{PRODUCT_NAME} — {PRODUCT_TAGLINE}", "", "Model family (targets, not released checkpoints):"]
    for profile in MODEL_FAMILY:
        size = (
            f"~{profile.target_parameters_millions}M params / ~{profile.target_weight_mb_fp16} MB FP16"
            if profile.target_parameters_millions is not None
            else "architecture/size decided by evidence"
        )
        lines.append(f"  {profile.display_name:16} {size}")
        lines.append(f"    {profile.purpose}")
    lines.extend(
        [
            "",
            "Rule: training completion is not a release. Each checkpoint must pass its target baseline.",
        ]
    )
    return "\n".join(lines)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="ourtts", description="ourTTS product tools")
    parser.add_argument("--json", action="store_true", help="Print the product manifest as JSON.")
    parser.add_argument("--model", help="Show one model-family target, e.g. atom or core.")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.model:
        try:
            profile = model_profile(args.model)
        except KeyError:
            choices = ", ".join(item.key for item in MODEL_FAMILY)
            parser = build_parser()
            parser.error(f"unknown model {args.model!r}; choose one of: {choices}")
        payload = profile.to_dict()
        if args.json:
            print(json.dumps(payload, ensure_ascii=False, indent=2))
        else:
            print(f"{profile.display_name}\n{profile.purpose}")
            print("priorities: " + ", ".join(profile.priority))
            print(f"status: {profile.status}")
        return 0

    if args.json:
        print(json.dumps(product_manifest(), ensure_ascii=False, indent=2))
    else:
        print(_human_family())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
