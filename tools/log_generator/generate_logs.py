#!/usr/bin/env python3
import argparse
import random
from datetime import datetime, timedelta
from pathlib import Path


LEVELS = ["INFO", "INFO", "INFO", "WARN", "ERROR", "DEBUG"]
SERVICES = ["auth", "api", "worker", "database", "scheduler", "billing"]
INFO_MESSAGES = [
    "request completed successfully",
    "user session refreshed",
    "background job finished",
    "cache lookup completed",
    "log ingestion checkpoint saved",
]
WARN_MESSAGES = [
    "request latency exceeded threshold",
    "retrying upstream service call",
    "disk usage is above warning level",
    "rate limit is close to capacity",
]
ERROR_MESSAGES = [
    "failed to connect to database",
    "unhandled exception while parsing payload",
    "upstream service returned 503",
    "authentication token validation failed",
]
DEBUG_MESSAGES = [
    "loaded runtime configuration",
    "received internal heartbeat",
    "resolved feature flag state",
]


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate sample log files for Log Assistant testing.")
    parser.add_argument("--files", type=int, default=5, help="Number of log files to generate.")
    parser.add_argument("--lines", type=int, default=120, help="Number of lines per file.")
    parser.add_argument("--output", default="sample_logs", help="Output directory for generated logs.")
    parser.add_argument("--seed", type=int, default=42, help="Random seed for reproducible output.")
    args = parser.parse_args()

    random.seed(args.seed)
    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)

    base_time = datetime.now().replace(microsecond=0) - timedelta(hours=args.files)

    for file_index in range(1, args.files + 1):
        file_path = output_dir / f"sample-{file_index:02d}.log"
        lines = build_log_lines(
            start_time=base_time + timedelta(minutes=file_index * 7),
            count=args.lines,
        )
        file_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    print(f"Generated {args.files} log files in {output_dir.resolve()}")


def build_log_lines(start_time: datetime, count: int) -> list[str]:
    lines: list[str] = []

    for line_number in range(1, count + 1):
        timestamp = start_time + timedelta(seconds=line_number * random.randint(2, 12))
        level = random.choice(LEVELS)
        service = random.choice(SERVICES)
        request_id = f"req-{random.randint(10000, 99999)}"
        message = choose_message(level)
        duration_ms = random.randint(8, 2200)
        user_id = random.randint(1, 80)

        lines.append(
            f"{timestamp.isoformat()} {level} service={service} "
            f"request_id={request_id} user_id={user_id} duration_ms={duration_ms} {message}"
        )

    return lines


def choose_message(level: str) -> str:
    if level == "WARN":
        return random.choice(WARN_MESSAGES)

    if level == "ERROR":
        return random.choice(ERROR_MESSAGES)

    if level == "DEBUG":
        return random.choice(DEBUG_MESSAGES)

    return random.choice(INFO_MESSAGES)


if __name__ == "__main__":
    main()
