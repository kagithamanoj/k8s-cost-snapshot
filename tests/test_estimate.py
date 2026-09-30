"""Tests for k8s-cost-snapshot."""

import pytest

from costsnap import (
    Workload,
    load_inventory,
    monthly_cost,
    parse_cpu,
    parse_memory,
    summarize,
)
from costsnap.cli import main


def test_parse_cpu():
    assert parse_cpu("500m") == 500
    assert parse_cpu("2") == 2000
    assert parse_cpu("0.5") == 500
    assert parse_cpu(1) == 1000
    assert parse_cpu(0.25) == 250


def test_parse_memory():
    assert parse_memory("512Mi") == 512
    assert parse_memory("2Gi") == 2048
    assert parse_memory("1G") == 976  # decimal GB to MiB
    assert parse_memory(256) == 256


def test_monthly_cost_math():
    w = Workload("api", "prod", cpu_millicores=1000, memory_mib=2048, replicas=2)
    # 2 cores * 0.05 + 4 GiB * 0.01 = 0.14 / hour -> * 730
    cost = monthly_cost(w, 0.05, 0.01)
    assert cost == pytest.approx(0.14 * 730)


def test_zero_requests_cost_nothing():
    w = Workload("idle", "dev", cpu_millicores=0, memory_mib=0)
    assert monthly_cost(w, 0.05, 0.01) == 0.0


def test_load_inventory_yaml(tmp_path):
    inv = tmp_path / "inv.yaml"
    inv.write_text(
        "- name: api\n"
        "  namespace: prod\n"
        "  cpu: 500m\n"
        "  memory: 512Mi\n"
        "  replicas: 3\n"
        "- name: worker\n"
        "  cpu: 1\n"
        "  memory: 1Gi\n"
    )
    workloads = load_inventory(str(inv))
    assert len(workloads) == 2
    assert workloads[0].cpu_millicores == 500
    assert workloads[0].memory_mib == 512
    assert workloads[0].replicas == 3
    assert workloads[1].namespace == "default"
    assert workloads[1].memory_mib == 1024


def test_summarize_groups_by_namespace():
    workloads = [
        Workload("a", "prod", 1000, 1024),
        Workload("b", "prod", 1000, 1024),
        Workload("c", "dev", 500, 512),
    ]
    report = summarize(workloads, 0.04, 0.005)
    assert report["namespaces"]["prod"]["workloads"] == 2
    assert report["namespaces"]["dev"]["workloads"] == 1
    total = sum(ns["monthly_cost"] for ns in report["namespaces"].values())
    assert report["total_monthly_cost"] == pytest.approx(total)


def test_cli_runs(tmp_path, capsys):
    inv = tmp_path / "inv.yaml"
    inv.write_text("- name: api\n  namespace: prod\n  cpu: 500m\n  memory: 512Mi\n")
    assert main([str(inv)]) == 0
    out = capsys.readouterr().out
    assert "prod" in out
    assert "TOTAL" in out
