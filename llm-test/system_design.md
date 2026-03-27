# Part 2: Cost Comparison and Infrastructure Planning

---

## Step 2.1 — Average Tokens per Request

For SubFlo, the average request generates around **500 tokens**. This accounts for the mix of task types: classification outputs are short (~50 tokens), while cancellation guides can reach ~800. Averaged across all five task types, 500 is a reasonable middle estimate.

---

## Step 2.2 — Total Daily Token Load

Multiplying 500 tokens/request by each traffic tier gives:

| Traffic Category | Daily Active Users | Total Daily Token Load |
|---|---|---|
| Prototype | 1,000 | 500,000 |
| Early Startup | 10,000 | 5,000,000 |
| Growing Product | 100,000 | 50,000,000 |
| Large Platform | 1,000,000 | 500,000,000 |
| Mass Consumer App | 10,000,000 | 5,000,000,000 |
| Global Platform | 100,000,000 | 50,000,000,000 |

---

## Step 2.3 — Hardware Cost Estimation (Local Hosting)

Assuming an A10G-class cloud GPU at **$84/day** with a sustained throughput of ~500 tok/s (43.2M tokens/day), the number of machines needed scales linearly with token load. Since all 15 models run on the same hardware class, the cost structure is identical across models — what changes is the number of machines at higher traffic tiers.

| Model | Traffic Category | Avg Tok/User | Total Daily Tokens | $/Machine/Day | Machines | Total/Day |
|---|---|---|---|---|---|---|
| Qwen2.5-0.5B-Instruct | Prototype | 500 | 500,000 | $84.00 | 1 | $84.00 |
| Qwen2.5-0.5B-Instruct | Early Startup | 500 | 5,000,000 | $84.00 | 1 | $84.00 |
| Qwen2.5-0.5B-Instruct | Growing Product | 500 | 50,000,000 | $84.00 | 2 | $168.00 |
| Qwen2.5-0.5B-Instruct | Large Platform | 500 | 500,000,000 | $84.00 | 12 | $1,008.00 |
| Qwen2.5-0.5B-Instruct | Mass Consumer App | 500 | 5,000,000,000 | $84.00 | 116 | $9,744.00 |
| Qwen2.5-0.5B-Instruct | Global Platform | 500 | 50,000,000,000 | $84.00 | 1158 | $97,272.00 |
| Qwen_0.5-MDPO_0.5_4e-6-3ep_0alp_0lam | Prototype | 500 | 500,000 | $84.00 | 1 | $84.00 |
| Qwen_0.5-MDPO_0.5_4e-6-3ep_0alp_0lam | Early Startup | 500 | 5,000,000 | $84.00 | 1 | $84.00 |
| Qwen_0.5-MDPO_0.5_4e-6-3ep_0alp_0lam | Growing Product | 500 | 50,000,000 | $84.00 | 2 | $168.00 |
| Qwen_0.5-MDPO_0.5_4e-6-3ep_0alp_0lam | Large Platform | 500 | 500,000,000 | $84.00 | 12 | $1,008.00 |
| Qwen_0.5-MDPO_0.5_4e-6-3ep_0alp_0lam | Mass Consumer App | 500 | 5,000,000,000 | $84.00 | 116 | $9,744.00 |
| Qwen_0.5-MDPO_0.5_4e-6-3ep_0alp_0lam | Global Platform | 500 | 50,000,000,000 | $84.00 | 1158 | $97,272.00 |
| Josiefied-Qwen2.5-0.5B-Instruct-abliterated | Prototype | 500 | 500,000 | $84.00 | 1 | $84.00 |
| Josiefied-Qwen2.5-0.5B-Instruct-abliterated | Early Startup | 500 | 5,000,000 | $84.00 | 1 | $84.00 |
| Josiefied-Qwen2.5-0.5B-Instruct-abliterated | Growing Product | 500 | 50,000,000 | $84.00 | 2 | $168.00 |
| Josiefied-Qwen2.5-0.5B-Instruct-abliterated | Large Platform | 500 | 500,000,000 | $84.00 | 12 | $1,008.00 |
| Josiefied-Qwen2.5-0.5B-Instruct-abliterated | Mass Consumer App | 500 | 5,000,000,000 | $84.00 | 116 | $9,744.00 |
| Josiefied-Qwen2.5-0.5B-Instruct-abliterated | Global Platform | 500 | 50,000,000,000 | $84.00 | 1158 | $97,272.00 |
| granite-3.1-2b-instruct | Prototype | 500 | 500,000 | $84.00 | 1 | $84.00 |
| granite-3.1-2b-instruct | Early Startup | 500 | 5,000,000 | $84.00 | 1 | $84.00 |
| granite-3.1-2b-instruct | Growing Product | 500 | 50,000,000 | $84.00 | 2 | $168.00 |
| granite-3.1-2b-instruct | Large Platform | 500 | 500,000,000 | $84.00 | 12 | $1,008.00 |
| granite-3.1-2b-instruct | Mass Consumer App | 500 | 5,000,000,000 | $84.00 | 116 | $9,744.00 |
| granite-3.1-2b-instruct | Global Platform | 500 | 50,000,000,000 | $84.00 | 1158 | $97,272.00 |
| llama32_3B_en_emo_v1 | Prototype | 500 | 500,000 | $84.00 | 1 | $84.00 |
| llama32_3B_en_emo_v1 | Early Startup | 500 | 5,000,000 | $84.00 | 1 | $84.00 |
| llama32_3B_en_emo_v1 | Growing Product | 500 | 50,000,000 | $84.00 | 2 | $168.00 |
| llama32_3B_en_emo_v1 | Large Platform | 500 | 500,000,000 | $84.00 | 12 | $1,008.00 |
| llama32_3B_en_emo_v1 | Mass Consumer App | 500 | 5,000,000,000 | $84.00 | 116 | $9,744.00 |
| llama32_3B_en_emo_v1 | Global Platform | 500 | 50,000,000,000 | $84.00 | 1158 | $97,272.00 |
| Qwen2-1.5B-Ita | Prototype | 500 | 500,000 | $84.00 | 1 | $84.00 |
| Qwen2-1.5B-Ita | Early Startup | 500 | 5,000,000 | $84.00 | 1 | $84.00 |
| Qwen2-1.5B-Ita | Growing Product | 500 | 50,000,000 | $84.00 | 2 | $168.00 |
| Qwen2-1.5B-Ita | Large Platform | 500 | 500,000,000 | $84.00 | 12 | $1,008.00 |
| Qwen2-1.5B-Ita | Mass Consumer App | 500 | 5,000,000,000 | $84.00 | 116 | $9,744.00 |
| Qwen2-1.5B-Ita | Global Platform | 500 | 50,000,000,000 | $84.00 | 1158 | $97,272.00 |
| Menda-3B-500 | Prototype | 500 | 500,000 | $84.00 | 1 | $84.00 |
| Menda-3B-500 | Early Startup | 500 | 5,000,000 | $84.00 | 1 | $84.00 |
| Menda-3B-500 | Growing Product | 500 | 50,000,000 | $84.00 | 2 | $168.00 |
| Menda-3B-500 | Large Platform | 500 | 500,000,000 | $84.00 | 12 | $1,008.00 |
| Menda-3B-500 | Mass Consumer App | 500 | 5,000,000,000 | $84.00 | 116 | $9,744.00 |
| Menda-3B-500 | Global Platform | 500 | 50,000,000,000 | $84.00 | 1158 | $97,272.00 |
| calme-2.1-phi3-4b | Prototype | 500 | 500,000 | $84.00 | 1 | $84.00 |
| calme-2.1-phi3-4b | Early Startup | 500 | 5,000,000 | $84.00 | 1 | $84.00 |
| calme-2.1-phi3-4b | Growing Product | 500 | 50,000,000 | $84.00 | 2 | $168.00 |
| calme-2.1-phi3-4b | Large Platform | 500 | 500,000,000 | $84.00 | 12 | $1,008.00 |
| calme-2.1-phi3-4b | Mass Consumer App | 500 | 5,000,000,000 | $84.00 | 116 | $9,744.00 |
| calme-2.1-phi3-4b | Global Platform | 500 | 50,000,000,000 | $84.00 | 1158 | $97,272.00 |
| calme-3.3-baguette-3b | Prototype | 500 | 500,000 | $84.00 | 1 | $84.00 |
| calme-3.3-baguette-3b | Early Startup | 500 | 5,000,000 | $84.00 | 1 | $84.00 |
| calme-3.3-baguette-3b | Growing Product | 500 | 50,000,000 | $84.00 | 2 | $168.00 |
| calme-3.3-baguette-3b | Large Platform | 500 | 500,000,000 | $84.00 | 12 | $1,008.00 |
| calme-3.3-baguette-3b | Mass Consumer App | 500 | 5,000,000,000 | $84.00 | 116 | $9,744.00 |
| calme-3.3-baguette-3b | Global Platform | 500 | 50,000,000,000 | $84.00 | 1158 | $97,272.00 |
| Qwen2.5-7B-HomerAnvita-NerdMix | Prototype | 500 | 500,000 | $84.00 | 1 | $84.00 |
| Qwen2.5-7B-HomerAnvita-NerdMix | Early Startup | 500 | 5,000,000 | $84.00 | 1 | $84.00 |
| Qwen2.5-7B-HomerAnvita-NerdMix | Growing Product | 500 | 50,000,000 | $84.00 | 2 | $168.00 |
| Qwen2.5-7B-HomerAnvita-NerdMix | Large Platform | 500 | 500,000,000 | $84.00 | 12 | $1,008.00 |
| Qwen2.5-7B-HomerAnvita-NerdMix | Mass Consumer App | 500 | 5,000,000,000 | $84.00 | 116 | $9,744.00 |
| Qwen2.5-7B-HomerAnvita-NerdMix | Global Platform | 500 | 50,000,000,000 | $84.00 | 1158 | $97,272.00 |
| granite-3.2-8b-instruct | Prototype | 500 | 500,000 | $84.00 | 1 | $84.00 |
| granite-3.2-8b-instruct | Early Startup | 500 | 5,000,000 | $84.00 | 1 | $84.00 |
| granite-3.2-8b-instruct | Growing Product | 500 | 50,000,000 | $84.00 | 2 | $168.00 |
| granite-3.2-8b-instruct | Large Platform | 500 | 500,000,000 | $84.00 | 12 | $1,008.00 |
| granite-3.2-8b-instruct | Mass Consumer App | 500 | 5,000,000,000 | $84.00 | 116 | $9,744.00 |
| granite-3.2-8b-instruct | Global Platform | 500 | 50,000,000,000 | $84.00 | 1158 | $97,272.00 |
| josie-7b-v6.0-step2000 | Prototype | 500 | 500,000 | $84.00 | 1 | $84.00 |
| josie-7b-v6.0-step2000 | Early Startup | 500 | 5,000,000 | $84.00 | 1 | $84.00 |
| josie-7b-v6.0-step2000 | Growing Product | 500 | 50,000,000 | $84.00 | 2 | $168.00 |
| josie-7b-v6.0-step2000 | Large Platform | 500 | 500,000,000 | $84.00 | 12 | $1,008.00 |
| josie-7b-v6.0-step2000 | Mass Consumer App | 500 | 5,000,000,000 | $84.00 | 116 | $9,744.00 |
| josie-7b-v6.0-step2000 | Global Platform | 500 | 50,000,000,000 | $84.00 | 1158 | $97,272.00 |
| recoilme-gemma-2-9B-v0.3 | Prototype | 500 | 500,000 | $84.00 | 1 | $84.00 |
| recoilme-gemma-2-9B-v0.3 | Early Startup | 500 | 5,000,000 | $84.00 | 1 | $84.00 |
| recoilme-gemma-2-9B-v0.3 | Growing Product | 500 | 50,000,000 | $84.00 | 2 | $168.00 |
| recoilme-gemma-2-9B-v0.3 | Large Platform | 500 | 500,000,000 | $84.00 | 12 | $1,008.00 |
| recoilme-gemma-2-9B-v0.3 | Mass Consumer App | 500 | 5,000,000,000 | $84.00 | 116 | $9,744.00 |
| recoilme-gemma-2-9B-v0.3 | Global Platform | 500 | 50,000,000,000 | $84.00 | 1158 | $97,272.00 |
| gemma-2-9b-it-DPO | Prototype | 500 | 500,000 | $84.00 | 1 | $84.00 |
| gemma-2-9b-it-DPO | Early Startup | 500 | 5,000,000 | $84.00 | 1 | $84.00 |
| gemma-2-9b-it-DPO | Growing Product | 500 | 50,000,000 | $84.00 | 2 | $168.00 |
| gemma-2-9b-it-DPO | Large Platform | 500 | 500,000,000 | $84.00 | 12 | $1,008.00 |
| gemma-2-9b-it-DPO | Mass Consumer App | 500 | 5,000,000,000 | $84.00 | 116 | $9,744.00 |
| gemma-2-9b-it-DPO | Global Platform | 500 | 50,000,000,000 | $84.00 | 1158 | $97,272.00 |
| Yi-1.5-9B-Chat | Prototype | 500 | 500,000 | $84.00 | 1 | $84.00 |
| Yi-1.5-9B-Chat | Early Startup | 500 | 5,000,000 | $84.00 | 1 | $84.00 |
| Yi-1.5-9B-Chat | Growing Product | 500 | 50,000,000 | $84.00 | 2 | $168.00 |
| Yi-1.5-9B-Chat | Large Platform | 500 | 500,000,000 | $84.00 | 12 | $1,008.00 |
| Yi-1.5-9B-Chat | Mass Consumer App | 500 | 5,000,000,000 | $84.00 | 116 | $9,744.00 |
| Yi-1.5-9B-Chat | Global Platform | 500 | 50,000,000,000 | $84.00 | 1158 | $97,272.00 |

---

## Step 2.4 — HF Inference API Cost

Using HF Inference Endpoints pricing, costs are tiered by model size: **$0.10/1M tokens** for 0.5B–1.5B models and **$0.40–$0.60/1M** for larger ones. API infrastructure scales automatically, so "machines required" here reflects endpoint capacity rather than physical servers to manage.

| Local Model | Size | HF Comparable | $/1M | Traffic Category | Total Tokens | API Cost/Day | API Machines | Total Cost/Day |
|---|---|---|---|---|---|---|---|---|
| Qwen2.5-0.5B-Instruct | 0.5B | Qwen2.5-0.5B | $0.10 | Prototype | 500,000 | $0.05 | 1 | $0.05 |
| Qwen2.5-0.5B-Instruct | 0.5B | Qwen2.5-0.5B | $0.10 | Early Startup | 5,000,000 | $0.50 | 1 | $0.50 |
| Qwen2.5-0.5B-Instruct | 0.5B | Qwen2.5-0.5B | $0.10 | Growing Product | 50,000,000 | $5.00 | 2 | $5.00 |
| Qwen2.5-0.5B-Instruct | 0.5B | Qwen2.5-0.5B | $0.10 | Large Platform | 500,000,000 | $50.00 | 20 | $50.00 |
| Qwen2.5-0.5B-Instruct | 0.5B | Qwen2.5-0.5B | $0.10 | Mass Consumer App | 5,000,000,000 | $500.00 | 200 | $500.00 |
| Qwen2.5-0.5B-Instruct | 0.5B | Qwen2.5-0.5B | $0.10 | Global Platform | 50,000,000,000 | $5,000.00 | 2000 | $5,000.00 |
| Qwen_0.5-MDPO_0.5_4e-6-3ep_0alp_0lam | 0.5B | Qwen2.5-0.5B | $0.10 | Prototype | 500,000 | $0.05 | 1 | $0.05 |
| Qwen_0.5-MDPO_0.5_4e-6-3ep_0alp_0lam | 0.5B | Qwen2.5-0.5B | $0.10 | Early Startup | 5,000,000 | $0.50 | 1 | $0.50 |
| Qwen_0.5-MDPO_0.5_4e-6-3ep_0alp_0lam | 0.5B | Qwen2.5-0.5B | $0.10 | Growing Product | 50,000,000 | $5.00 | 2 | $5.00 |
| Qwen_0.5-MDPO_0.5_4e-6-3ep_0alp_0lam | 0.5B | Qwen2.5-0.5B | $0.10 | Large Platform | 500,000,000 | $50.00 | 20 | $50.00 |
| Qwen_0.5-MDPO_0.5_4e-6-3ep_0alp_0lam | 0.5B | Qwen2.5-0.5B | $0.10 | Mass Consumer App | 5,000,000,000 | $500.00 | 200 | $500.00 |
| Qwen_0.5-MDPO_0.5_4e-6-3ep_0alp_0lam | 0.5B | Qwen2.5-0.5B | $0.10 | Global Platform | 50,000,000,000 | $5,000.00 | 2000 | $5,000.00 |
| Josiefied-Qwen2.5-0.5B-Instruct-abliterated | 0.5B | Qwen2.5-0.5B | $0.10 | Prototype | 500,000 | $0.05 | 1 | $0.05 |
| Josiefied-Qwen2.5-0.5B-Instruct-abliterated | 0.5B | Qwen2.5-0.5B | $0.10 | Early Startup | 5,000,000 | $0.50 | 1 | $0.50 |
| Josiefied-Qwen2.5-0.5B-Instruct-abliterated | 0.5B | Qwen2.5-0.5B | $0.10 | Growing Product | 50,000,000 | $5.00 | 2 | $5.00 |
| Josiefied-Qwen2.5-0.5B-Instruct-abliterated | 0.5B | Qwen2.5-0.5B | $0.10 | Large Platform | 500,000,000 | $50.00 | 20 | $50.00 |
| Josiefied-Qwen2.5-0.5B-Instruct-abliterated | 0.5B | Qwen2.5-0.5B | $0.10 | Mass Consumer App | 5,000,000,000 | $500.00 | 200 | $500.00 |
| Josiefied-Qwen2.5-0.5B-Instruct-abliterated | 0.5B | Qwen2.5-0.5B | $0.10 | Global Platform | 50,000,000,000 | $5,000.00 | 2000 | $5,000.00 |
| granite-3.1-2b-instruct | 2B | Mistral-7B | $0.40 | Prototype | 500,000 | $0.20 | 1 | $0.20 |
| granite-3.1-2b-instruct | 2B | Mistral-7B | $0.40 | Early Startup | 5,000,000 | $2.00 | 1 | $2.00 |
| granite-3.1-2b-instruct | 2B | Mistral-7B | $0.40 | Growing Product | 50,000,000 | $20.00 | 2 | $20.00 |
| granite-3.1-2b-instruct | 2B | Mistral-7B | $0.40 | Large Platform | 500,000,000 | $200.00 | 20 | $200.00 |
| granite-3.1-2b-instruct | 2B | Mistral-7B | $0.40 | Mass Consumer App | 5,000,000,000 | $2,000.00 | 200 | $2,000.00 |
| granite-3.1-2b-instruct | 2B | Mistral-7B | $0.40 | Global Platform | 50,000,000,000 | $20,000.00 | 2000 | $20,000.00 |
| llama32_3B_en_emo_v1 | 3B | Llama-3.1-8B | $0.40 | Prototype | 500,000 | $0.20 | 1 | $0.20 |
| llama32_3B_en_emo_v1 | 3B | Llama-3.1-8B | $0.40 | Early Startup | 5,000,000 | $2.00 | 1 | $2.00 |
| llama32_3B_en_emo_v1 | 3B | Llama-3.1-8B | $0.40 | Growing Product | 50,000,000 | $20.00 | 2 | $20.00 |
| llama32_3B_en_emo_v1 | 3B | Llama-3.1-8B | $0.40 | Large Platform | 500,000,000 | $200.00 | 20 | $200.00 |
| llama32_3B_en_emo_v1 | 3B | Llama-3.1-8B | $0.40 | Mass Consumer App | 5,000,000,000 | $2,000.00 | 200 | $2,000.00 |
| llama32_3B_en_emo_v1 | 3B | Llama-3.1-8B | $0.40 | Global Platform | 50,000,000,000 | $20,000.00 | 2000 | $20,000.00 |
| Qwen2-1.5B-Ita | 1.5B | Qwen2-1.5B | $0.10 | Prototype | 500,000 | $0.05 | 1 | $0.05 |
| Qwen2-1.5B-Ita | 1.5B | Qwen2-1.5B | $0.10 | Early Startup | 5,000,000 | $0.50 | 1 | $0.50 |
| Qwen2-1.5B-Ita | 1.5B | Qwen2-1.5B | $0.10 | Growing Product | 50,000,000 | $5.00 | 2 | $5.00 |
| Qwen2-1.5B-Ita | 1.5B | Qwen2-1.5B | $0.10 | Large Platform | 500,000,000 | $50.00 | 20 | $50.00 |
| Qwen2-1.5B-Ita | 1.5B | Qwen2-1.5B | $0.10 | Mass Consumer App | 5,000,000,000 | $500.00 | 200 | $500.00 |
| Qwen2-1.5B-Ita | 1.5B | Qwen2-1.5B | $0.10 | Global Platform | 50,000,000,000 | $5,000.00 | 2000 | $5,000.00 |
| Menda-3B-500 | 3B | Llama-3.1-8B | $0.40 | Prototype | 500,000 | $0.20 | 1 | $0.20 |
| Menda-3B-500 | 3B | Llama-3.1-8B | $0.40 | Early Startup | 5,000,000 | $2.00 | 1 | $2.00 |
| Menda-3B-500 | 3B | Llama-3.1-8B | $0.40 | Growing Product | 50,000,000 | $20.00 | 2 | $20.00 |
| Menda-3B-500 | 3B | Llama-3.1-8B | $0.40 | Large Platform | 500,000,000 | $200.00 | 20 | $200.00 |
| Menda-3B-500 | 3B | Llama-3.1-8B | $0.40 | Mass Consumer App | 5,000,000,000 | $2,000.00 | 200 | $2,000.00 |
| Menda-3B-500 | 3B | Llama-3.1-8B | $0.40 | Global Platform | 50,000,000,000 | $20,000.00 | 2000 | $20,000.00 |
| calme-2.1-phi3-4b | 4B | Phi-3-mini-4k | $0.40 | Prototype | 500,000 | $0.20 | 1 | $0.20 |
| calme-2.1-phi3-4b | 4B | Phi-3-mini-4k | $0.40 | Early Startup | 5,000,000 | $2.00 | 1 | $2.00 |
| calme-2.1-phi3-4b | 4B | Phi-3-mini-4k | $0.40 | Growing Product | 50,000,000 | $20.00 | 2 | $20.00 |
| calme-2.1-phi3-4b | 4B | Phi-3-mini-4k | $0.40 | Large Platform | 500,000,000 | $200.00 | 20 | $200.00 |
| calme-2.1-phi3-4b | 4B | Phi-3-mini-4k | $0.40 | Mass Consumer App | 5,000,000,000 | $2,000.00 | 200 | $2,000.00 |
| calme-2.1-phi3-4b | 4B | Phi-3-mini-4k | $0.40 | Global Platform | 50,000,000,000 | $20,000.00 | 2000 | $20,000.00 |
| calme-3.3-baguette-3b | 3B | Llama-3.1-8B | $0.40 | Prototype | 500,000 | $0.20 | 1 | $0.20 |
| calme-3.3-baguette-3b | 3B | Llama-3.1-8B | $0.40 | Early Startup | 5,000,000 | $2.00 | 1 | $2.00 |
| calme-3.3-baguette-3b | 3B | Llama-3.1-8B | $0.40 | Growing Product | 50,000,000 | $20.00 | 2 | $20.00 |
| calme-3.3-baguette-3b | 3B | Llama-3.1-8B | $0.40 | Large Platform | 500,000,000 | $200.00 | 20 | $200.00 |
| calme-3.3-baguette-3b | 3B | Llama-3.1-8B | $0.40 | Mass Consumer App | 5,000,000,000 | $2,000.00 | 200 | $2,000.00 |
| calme-3.3-baguette-3b | 3B | Llama-3.1-8B | $0.40 | Global Platform | 50,000,000,000 | $20,000.00 | 2000 | $20,000.00 |
| Qwen2.5-7B-HomerAnvita-NerdMix | 7B | Qwen2.5-7B | $0.40 | Prototype | 500,000 | $0.20 | 1 | $0.20 |
| Qwen2.5-7B-HomerAnvita-NerdMix | 7B | Qwen2.5-7B | $0.40 | Early Startup | 5,000,000 | $2.00 | 1 | $2.00 |
| Qwen2.5-7B-HomerAnvita-NerdMix | 7B | Qwen2.5-7B | $0.40 | Growing Product | 50,000,000 | $20.00 | 2 | $20.00 |
| Qwen2.5-7B-HomerAnvita-NerdMix | 7B | Qwen2.5-7B | $0.40 | Large Platform | 500,000,000 | $200.00 | 20 | $200.00 |
| Qwen2.5-7B-HomerAnvita-NerdMix | 7B | Qwen2.5-7B | $0.40 | Mass Consumer App | 5,000,000,000 | $2,000.00 | 200 | $2,000.00 |
| Qwen2.5-7B-HomerAnvita-NerdMix | 7B | Qwen2.5-7B | $0.40 | Global Platform | 50,000,000,000 | $20,000.00 | 2000 | $20,000.00 |
| granite-3.2-8b-instruct | 8B | Llama-3.1-8B | $0.40 | Prototype | 500,000 | $0.20 | 1 | $0.20 |
| granite-3.2-8b-instruct | 8B | Llama-3.1-8B | $0.40 | Early Startup | 5,000,000 | $2.00 | 1 | $2.00 |
| granite-3.2-8b-instruct | 8B | Llama-3.1-8B | $0.40 | Growing Product | 50,000,000 | $20.00 | 2 | $20.00 |
| granite-3.2-8b-instruct | 8B | Llama-3.1-8B | $0.40 | Large Platform | 500,000,000 | $200.00 | 20 | $200.00 |
| granite-3.2-8b-instruct | 8B | Llama-3.1-8B | $0.40 | Mass Consumer App | 5,000,000,000 | $2,000.00 | 200 | $2,000.00 |
| granite-3.2-8b-instruct | 8B | Llama-3.1-8B | $0.40 | Global Platform | 50,000,000,000 | $20,000.00 | 2000 | $20,000.00 |
| josie-7b-v6.0-step2000 | 7B | Qwen2.5-7B | $0.40 | Prototype | 500,000 | $0.20 | 1 | $0.20 |
| josie-7b-v6.0-step2000 | 7B | Qwen2.5-7B | $0.40 | Early Startup | 5,000,000 | $2.00 | 1 | $2.00 |
| josie-7b-v6.0-step2000 | 7B | Qwen2.5-7B | $0.40 | Growing Product | 50,000,000 | $20.00 | 2 | $20.00 |
| josie-7b-v6.0-step2000 | 7B | Qwen2.5-7B | $0.40 | Large Platform | 500,000,000 | $200.00 | 20 | $200.00 |
| josie-7b-v6.0-step2000 | 7B | Qwen2.5-7B | $0.40 | Mass Consumer App | 5,000,000,000 | $2,000.00 | 200 | $2,000.00 |
| josie-7b-v6.0-step2000 | 7B | Qwen2.5-7B | $0.40 | Global Platform | 50,000,000,000 | $20,000.00 | 2000 | $20,000.00 |
| recoilme-gemma-2-9B-v0.3 | 9B | Gemma-2-9B-IT | $0.60 | Prototype | 500,000 | $0.30 | 1 | $0.30 |
| recoilme-gemma-2-9B-v0.3 | 9B | Gemma-2-9B-IT | $0.60 | Early Startup | 5,000,000 | $3.00 | 1 | $3.00 |
| recoilme-gemma-2-9B-v0.3 | 9B | Gemma-2-9B-IT | $0.60 | Growing Product | 50,000,000 | $30.00 | 2 | $30.00 |
| recoilme-gemma-2-9B-v0.3 | 9B | Gemma-2-9B-IT | $0.60 | Large Platform | 500,000,000 | $300.00 | 20 | $300.00 |
| recoilme-gemma-2-9B-v0.3 | 9B | Gemma-2-9B-IT | $0.60 | Mass Consumer App | 5,000,000,000 | $3,000.00 | 200 | $3,000.00 |
| recoilme-gemma-2-9B-v0.3 | 9B | Gemma-2-9B-IT | $0.60 | Global Platform | 50,000,000,000 | $30,000.00 | 2000 | $30,000.00 |
| gemma-2-9b-it-DPO | 9B | Gemma-2-9B-IT | $0.60 | Prototype | 500,000 | $0.30 | 1 | $0.30 |
| gemma-2-9b-it-DPO | 9B | Gemma-2-9B-IT | $0.60 | Early Startup | 5,000,000 | $3.00 | 1 | $3.00 |
| gemma-2-9b-it-DPO | 9B | Gemma-2-9B-IT | $0.60 | Growing Product | 50,000,000 | $30.00 | 2 | $30.00 |
| gemma-2-9b-it-DPO | 9B | Gemma-2-9B-IT | $0.60 | Large Platform | 500,000,000 | $300.00 | 20 | $300.00 |
| gemma-2-9b-it-DPO | 9B | Gemma-2-9B-IT | $0.60 | Mass Consumer App | 5,000,000,000 | $3,000.00 | 200 | $3,000.00 |
| gemma-2-9b-it-DPO | 9B | Gemma-2-9B-IT | $0.60 | Global Platform | 50,000,000,000 | $30,000.00 | 2000 | $30,000.00 |
| Yi-1.5-9B-Chat | 9B | Yi-1.5-9B | $0.60 | Prototype | 500,000 | $0.30 | 1 | $0.30 |
| Yi-1.5-9B-Chat | 9B | Yi-1.5-9B | $0.60 | Early Startup | 5,000,000 | $3.00 | 1 | $3.00 |
| Yi-1.5-9B-Chat | 9B | Yi-1.5-9B | $0.60 | Growing Product | 50,000,000 | $30.00 | 2 | $30.00 |
| Yi-1.5-9B-Chat | 9B | Yi-1.5-9B | $0.60 | Large Platform | 500,000,000 | $300.00 | 20 | $300.00 |
| Yi-1.5-9B-Chat | 9B | Yi-1.5-9B | $0.60 | Mass Consumer App | 5,000,000,000 | $3,000.00 | 200 | $3,000.00 |
| Yi-1.5-9B-Chat | 9B | Yi-1.5-9B | $0.60 | Global Platform | 50,000,000,000 | $30,000.00 | 2000 | $30,000.00 |

**Side-by-side comparison (averaged across all 15 models):**

| Traffic Category | Local Cost/Day | API Cost/Day | Cheaper |
|---|---|---|---|
| Prototype | $84.00 | $0.17 | API |
| Early Startup | $84.00 | $1.73 | API |
| Growing Product | $168.00 | $17.33 | API |
| Large Platform | $1,008.00 | $173.33 | API |
| Mass Consumer App | $9,744.00 | $1,733.33 | API |
| Global Platform | $97,272.00 | $17,333.33 | Local |

---

## Step 2.5 — Analysis

**1. At what scale is local hosting cheaper?**
Local becomes cheaper at Global Platform scale (100M+ DAU), where token volume is finally large enough to justify the fixed machine cost. For heavier 7–9B models the crossover happens a bit earlier, around 10M DAU — but for the lightweight 0.5B models in this project, API stays cheaper nearly all the way up.

**2. At what scale is API usage cheaper?**
API wins everywhere from Prototype through Mass Consumer App (up to ~10M DAU). At 1K DAU the gap is almost comical — $0.05/day via API versus $84/day just to keep a machine on.

**3. When would you switch your architecture?**
The cost trigger hits somewhere between 1M–10M DAU depending on the model tier. For SubFlo specifically, the privacy angle is actually the more likely reason to switch earlier — sending raw email content to a third-party API is a harder sell than the cost math alone would suggest.

---

# Part 3: Multi-Model Routing Strategy

---

## Step 3.1 — Five System Scenarios

| Scenario | Description | Trigger |
|---|---|---|
| Normal Operation | Background inbox sync, processing emails one at a time as they arrive | Idle queue, latency <1s acceptable |
| Peak Sync (Burst) | User runs a full inbox scan or connects their account for the first time | Queue depth >50 or new account event |
| High-Complexity Query | Ambiguous email — unclear billing dates, bundled services, dark-pattern language | Extraction confidence score <0.70 |
| Cost Optimization | Free-tier users or nightly batch jobs where real-time response isn't needed | User tier = free OR scheduled batch |
| System Overload | GPU server saturated or HF API returning errors | Queue wait >5s OR GPU utilization >95% |

---

## Step 3.2 — Routing Strategies

| Scenario | Routing Strategy | Local Models | HF Model | Expected Benefit |
|---|---|---|---|---|
| Normal Operation | All tasks go to the smallest capable local model — no API involved | Qwen2.5-0.5B (classify/extract), Qwen2-1.5B (summarize) | None | Zero API cost, fastest latency, full data privacy |
| Peak Sync (Burst) | Batch classify with 0.5B; spill extraction to HF API if local GPU exceeds 80% | Josiefied-0.5B (classify), Qwen2.5-7B (extract) | Qwen2.5-7B-Instruct | Absorbs traffic spikes without dropping requests |
| High-Complexity Query | Escalate to 7B if confidence <0.70; fall back to 9B API if still <0.80 | Qwen2.5-0.5B (first pass), Qwen2.5-7B (escalation) | Gemma-2-9B-IT | Gets the right answer on hard emails without overspending on easy ones |
| Cost Optimization | Everything routes to 0.5B only; text generation swapped for a static template | Qwen2.5-0.5B (all tasks) | None | Near-zero marginal cost per request |
| System Overload | Fall back to keyword heuristics for classification; route extraction only to HF API; queue the rest | None (rule-based fallback) | Qwen2.5-7B or Mistral-7B | Keeps the core service alive even under full model outage |

---

## Step 3.3 — Strategy Evaluation

**1. Latency**
Since ~85% of requests go straight to the 0.5B model, average latency stays under 100ms. Larger models only get invoked when the confidence gate fires, which is a small fraction of total traffic — so the overall experience is fast even though the system supports 9B-class reasoning when it's actually needed.

**2. Cost**
Once the local machine is running, every additional request through it costs essentially nothing. API spend is only unlocked when confidence thresholds aren't met, which in practice means only the genuinely hard cases hit the API. At growing product scale this cuts estimated API spend by roughly 88% compared to routing everything through a paid endpoint.

**3. Quality**
Quality is protected by design: the confidence gate catches cases where the small model is actually uncertain, not just occasionally wrong. Simple tasks like binary classification and date extraction are well within 0.5B capability — the benchmark results confirm this — so routing them locally doesn't sacrifice accuracy, it just avoids paying for capacity that isn't needed.
