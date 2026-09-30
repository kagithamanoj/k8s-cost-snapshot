"""Command line interface for k8s-cost-snapshot."""

from __future__ import annotations

import argparse
import sys

from costsnap import load_inventory, summarize


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="k8s-cost-snapshot",
        description="Estimate monthly Kubernetes cost per namespace "
        "from resource requests.",
    )
    parser.add_argument("inventory", help="YAML/JSON inventory of workloads")
    parser.add_argument(
        "--cpu-price",
        type=float,
        default=0.04,
        help="Price per vCPU hour in USD (default: 0.04)",
    )
    parser.add_argument(
        "--mem-price",
        type=float,
        default=0.005,
        help="Price per GB hour in USD (default: 0.005)",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    workloads = load_inventory(args.inventory)
    report = summarize(workloads, args.cpu_price, args.mem_price)
    print(f"{'NAMESPACE':<20} {'WORKLOADS':>9} {'USD/MONTH':>10}")
    for namespace in sorted(report["namespaces"]):
        ns = report["namespaces"][namespace]
        print(f"{namespace:<20} {ns['workloads']:>9} {ns['monthly_cost']:>10.2f}")
    print(f"{'TOTAL':<20} {'':>9} {report['total_monthly_cost']:>10.2f}")
    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
