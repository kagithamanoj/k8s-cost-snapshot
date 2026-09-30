"""Cost estimation from Kubernetes resource requests.

The model is deliberately simple: monthly cost = requests x replicas x
hours-per-month x unit price. It answers "roughly what does this namespace
cost us" without a billing integration.
"""

from __future__ import annotations

from dataclasses import dataclass

HOURS_PER_MONTH = 730


@dataclass
class Workload:
    name: str
    namespace: str
    cpu_millicores: int
    memory_mib: int
    replicas: int = 1


def parse_cpu(value: str | int | float) -> int:
    """Parse a CPU quantity into millicores. Accepts '500m', '2', 2."""
    if isinstance(value, (int, float)):
        return int(value * 1000)
    text = str(value).strip()
    if text.endswith("m"):
        return int(text[:-1])
    return int(float(text) * 1000)


def parse_memory(value: str | int | float) -> int:
    """Parse a memory quantity into MiB. Accepts '512Mi', '2Gi', 512."""
    if isinstance(value, (int, float)):
        return int(value)
    text = str(value).strip()
    if text.endswith("Mi"):
        return int(text[:-2])
    if text.endswith("Gi"):
        return int(float(text[:-2]) * 1024)
    if text.endswith("M"):
        return int(float(text[:-1]) * 1000 / 1024)
    if text.endswith("G"):
        return int(float(text[:-1]) * 1000 * 1000 / 1024)
    return int(text)


def monthly_cost(
    workload: Workload,
    cpu_price_per_core_hour: float,
    mem_price_per_gb_hour: float,
) -> float:
    """Monthly cost for one workload at the given unit prices."""
    cores = workload.cpu_millicores / 1000 * workload.replicas
    gib = workload.memory_mib / 1024 * workload.replicas
    return (cores * cpu_price_per_core_hour + gib * mem_price_per_gb_hour) * HOURS_PER_MONTH


def load_inventory(path: str) -> list[Workload]:
    """Load workloads from a YAML or JSON inventory file.

    Each entry: {name, namespace, cpu, memory, replicas?}.
    cpu and memory use Kubernetes quantity strings like '500m' and '512Mi'.
    """
    with open(path, "r", encoding="utf-8") as fh:
        text = fh.read()
    if path.endswith(".json"):
        import json

        entries = json.loads(text)
    else:
        try:
            import yaml
        except ImportError as exc:
            raise RuntimeError(
                "PyYAML is required to read YAML inventories (pip install pyyaml)"
            ) from exc
        entries = yaml.safe_load(text)
    workloads = []
    for entry in entries or []:
        workloads.append(
            Workload(
                name=entry["name"],
                namespace=entry.get("namespace", "default"),
                cpu_millicores=parse_cpu(entry.get("cpu", "0")),
                memory_mib=parse_memory(entry.get("memory", "0")),
                replicas=int(entry.get("replicas", 1)),
            )
        )
    return workloads


def summarize(
    workloads: list[Workload],
    cpu_price_per_core_hour: float,
    mem_price_per_gb_hour: float,
) -> dict:
    """Return per-namespace totals plus a grand total."""
    by_namespace: dict[str, dict] = {}
    for w in workloads:
        cost = monthly_cost(w, cpu_price_per_core_hour, mem_price_per_gb_hour)
        ns = by_namespace.setdefault(
            w.namespace, {"workloads": 0, "monthly_cost": 0.0}
        )
        ns["workloads"] += 1
        ns["monthly_cost"] += cost
    total = sum(ns["monthly_cost"] for ns in by_namespace.values())
    return {"namespaces": by_namespace, "total_monthly_cost": total}
