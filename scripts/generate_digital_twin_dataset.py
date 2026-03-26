from __future__ import annotations

import argparse
import random
import sys
from pathlib import Path

import numpy as np


DEFAULT_OUTPUT = Path(__file__).resolve().parents[1] / "data" / "digital_twin_balanced_5000_seed42.csv"
PROJECT_DEFAULT_ROOT = Path(__file__).resolve().parents[2] / "Agrisense-Project-default"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate the rich AgriSense digital twin CSV used for InfluxDB seeding")
    parser.add_argument("--samples", type=int, default=5000, help="Target sample count for the balanced dataset")
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT), help="Output CSV path")
    parser.add_argument("--project-root", default=str(PROJECT_DEFAULT_ROOT), help="Path to the Agrisense-Project-default repo")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    project_root = Path(args.project_root).resolve()
    output_path = Path(args.output).resolve()

    if not project_root.exists():
        raise FileNotFoundError(f"Project root not found: {project_root}")

    sys.path.insert(0, str(project_root))

    from digital_twin import SyntheticDataGenerator

    random.seed(42)
    np.random.seed(42)

    output_path.parent.mkdir(parents=True, exist_ok=True)

    generator = SyntheticDataGenerator(output_dir=str(output_path.parent))
    dataframe = generator.generate_balanced_dataset(total_samples=args.samples)
    dataframe.to_csv(output_path, index=False)

    print(f"[agrisense] Generated {len(dataframe):,} rich digital twin rows")
    print(f"[agrisense] Output CSV: {output_path}")


if __name__ == "__main__":
    main()