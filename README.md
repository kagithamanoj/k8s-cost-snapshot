# k8s-cost-snapshot

Roughly what does each namespace cost us per month? Point this CLI at a
YAML inventory of workload resource requests and get a per-namespace cost
breakdown. No billing integration, no cluster access needed.

## The model

Monthly cost = requests x replicas x 730 hours x unit price. Simple on
purpose. Good enough for chargeback conversations and right-sizing reviews.

## Install

```bash
pip install k8s-cost-snapshot
```

## Use

Write an inventory file:

```yaml
- name: checkout-api
  namespace: prod
  cpu: 500m
  memory: 512Mi
  replicas: 3
- name: order-worker
  namespace: prod
  cpu: "1"
  memory: 1Gi
  replicas: 2
```

Then run:

```bash
k8s-cost-snapshot inventory.yaml --cpu-price 0.04 --mem-price 0.005
```

Output:

```
NAMESPACE            WORKLOADS  USD/MONTH
prod                       2      89.43
TOTAL                                89.43
```

CPU and memory accept Kubernetes quantity strings (`500m`, `2`, `512Mi`,
`2Gi`). Prices default to rough on-demand rates; pass your own to match
your cloud bill.

## License

MIT
