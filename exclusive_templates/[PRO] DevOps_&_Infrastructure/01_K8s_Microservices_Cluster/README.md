# ☸️ Kubernetes (K8s) Enterprise DevOps Pack

> **Estimated Market Value: $399+** (Enterprise DevOps setups & IaC Templates)

A complete, production-ready Kubernetes setup utilizing Helm, Ingress NGINX, and Cert-Manager. Built for SaaS applications handling millions of requests with auto-scaling architectures.

## What's Included:
1. `saas-deployment.yaml`: Defines the Next.js frontend and Node.js backend deployments.
2. `hpa.yaml`: Horizontal Pod Autoscalers (scale pods from 2 to 20 automatically based on CPU/Memory load).
3. `redis-statefulset.yaml`: HA Redis setup for sessions and rate limiting.
4. `ingress.yaml`: Rules for routing traffic from the load balancer directly to the correct internal cluster services.
5. `cert-manager/`: Automatically issues and renews Let's Encrypt SSL certificates for wildcard SaaS subdomains.
6. `postgres-operator/`: Best practices for running HA PostgreSQL databases inside K8s without outsourcing to AWS RDS.

## 🚀 How to Apply to Your Cluster
Ensure you have `kubectl` connected to your AWS EKS, Google GKE, or DigitalOcean Kubernetes context.

```bash
kubectl apply -f namespaces.yaml
kubectl apply -f saas-deployment.yaml
kubectl apply -f ingress.yaml
kubectl apply -f hpa.yaml
```

**Saves AWS consultants $300/hr from writing this exact manifest structure.**
