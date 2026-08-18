import argparse
import json
import sys


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--describe", action="store_true")
    parser.add_argument("--text")
    parser.add_argument("--output")
    args = parser.parse_args(argv)
    if args.describe:
        print(
            json.dumps(
                {
                    "schema_version": 1,
                    "engine": "vibevoice_realtime",
                    "adapter_version": "0.1.0",
                    "capabilities": {"streaming": True, "long_form": True, "voice_cloning": False},
                    "qualification": "blocked_pending_official_inference_contract_and_use_policy",
                }
            )
        )
        return 0
    print(
        json.dumps(
            {
                "error": "blocked",
                "message": "Synthesis intentionally blocked until the current official realtime inference contract and use restrictions are encoded and qualified.",
            }
        ),
        file=sys.stderr,
    )
    return 6


if __name__ == "__main__":
    raise SystemExit(main())
