# Mohiddin

### Applied AI Engineer · RAG pipelines · Agent workflows · LLM evaluation

I'm an applied AI engineer. I build production RAG pipelines, agent workflows and LLM evaluations on top of a data engineering foundation. I'm AWS certified in machine learning, data engineering and solutions architecture, and I co-authored a 2026 paper that benchmarks LLMs and encoder transformers on multi-label political event attribution.

```python
class Mohiddin:
    role = "Applied AI Engineer"
    builds = ["production RAG", "agent workflows", "LLM evals"]
    foundation = "data engineering"
    certified = ["AWS ML Engineer", "AWS Data Engineer", "AWS Solutions Architect"]
    off_duty = "photography"

    def ship(self, change):
        if self.evals(change).passed:
            return deploy(change)
        # evals failed, so nothing ships
```

## How I build

I like building useful things. Most of what I make starts with a problem I ran into myself. I own the problem, check whether other people have it too, and then build it for them. I try to solve the bigger picture instead of my one case.

[ai-message-sender](https://github.com/mohiddin7/ai-message-sender) is a good example. I needed to send scheduled messages to AI chat apps from my browser. I could have hard-coded a few sites. Instead I built a DOM picker, so it works on any website that has an input box and a send button.

## Currently working on

<!-- CURRENTLY:START -->
- [**Warmhop Link Tracker**](https://warmhop.com/try): A link tracker for job seekers: put it on your resume and see when someone clicks
- **IndexCase**: Threat intelligence for AI agents that traces how prompt injection spreads, in design
- [**getmeme**](https://getmeme.warmhop.com): An API that turns a prompt into one short, safety-checked line of copy
- [**adpilot**](https://github.com/mohiddin7/adpilot): AI analyst for ad spend: ask in plain English, get guarded SQL, answers and charts
<!-- CURRENTLY:END -->

<sub>Generated daily from my recent commits.</sub>

## Projects

- **[adpilot](https://github.com/mohiddin7/adpilot)** ([live demo](https://adpilot.streamlit.app/)): ask about ad spend in plain English and get guarded SQL, answers and charts. Its nightly eval scores 89.8 out of 100, with all 41 red-team cases passed, and every change runs through an eval gate.
- **[Warmhop Link Tracker](https://warmhop.com/try)**: a link tracker for job seekers. Put the link on your resume and you see when someone clicks it. It's live now.
- **[getmeme](https://getmeme.warmhop.com)**: an API that turns a prompt into one short, safety-checked line of copy. Text lines work today. GIF and image versions are in progress.
- **[ai-message-sender](https://github.com/mohiddin7/ai-message-sender)**: a Chrome extension that schedules prompts to Claude, ChatGPT, Gemini and any other site with an input box and a send button.
- **[code-satp](https://github.com/eteitelbaum/code-satp)** and **[SATP_hosting](https://github.com/mohiddin7/SATP_hosting)**: the pipeline and the hosted app from the same project as my paper. Transformer models that code event descriptions into multiple labels.
- **[News summarization](https://github.com/meetdaxini/NLP-News-Summarization)**: fine-tuned summarization models behind a Streamlit app.

## Tech stack

| | |
| --- | --- |
| **Languages** | ![Python](https://img.shields.io/badge/Python-2b3137?style=flat-square&logo=python&logoColor=3776AB) ![SQL](https://img.shields.io/badge/SQL-2b3137?style=flat-square) ![TypeScript](https://img.shields.io/badge/TypeScript-2b3137?style=flat-square&logo=typescript&logoColor=3178C6) ![JavaScript](https://img.shields.io/badge/JavaScript-2b3137?style=flat-square&logo=javascript&logoColor=F7DF1E) ![Java](https://img.shields.io/badge/Java-2b3137?style=flat-square&logo=openjdk&logoColor=ffffff) ![C++](https://img.shields.io/badge/C%2B%2B-2b3137?style=flat-square&logo=cplusplus&logoColor=00599C) ![R](https://img.shields.io/badge/R-2b3137?style=flat-square&logo=r&logoColor=276DC3) |
| **GenAI and agents** | ![Amazon Bedrock](https://img.shields.io/badge/Amazon%20Bedrock-2b3137?style=flat-square) ![Bedrock AgentCore](https://img.shields.io/badge/Bedrock%20AgentCore-2b3137?style=flat-square) ![Strands Agents](https://img.shields.io/badge/Strands%20Agents-2b3137?style=flat-square) ![LangChain](https://img.shields.io/badge/LangChain-2b3137?style=flat-square&logo=langchain&logoColor=7FC8FF) ![LangGraph](https://img.shields.io/badge/LangGraph-2b3137?style=flat-square&logo=langgraph&logoColor=7FC8FF) ![LlamaIndex](https://img.shields.io/badge/LlamaIndex-2b3137?style=flat-square) ![Pydantic AI](https://img.shields.io/badge/Pydantic%20AI-2b3137?style=flat-square&logo=pydantic&logoColor=E92063) ![MCP](https://img.shields.io/badge/MCP-2b3137?style=flat-square&logo=modelcontextprotocol&logoColor=ffffff) ![OpenAI API](https://img.shields.io/badge/OpenAI%20API-2b3137?style=flat-square) ![Anthropic API](https://img.shields.io/badge/Anthropic%20API-2b3137?style=flat-square&logo=anthropic&logoColor=ffffff) ![Hugging Face](https://img.shields.io/badge/Hugging%20Face-2b3137?style=flat-square&logo=huggingface&logoColor=FFD21E) |
| **ML** | ![PyTorch](https://img.shields.io/badge/PyTorch-2b3137?style=flat-square&logo=pytorch&logoColor=EE4C2C) ![TensorFlow](https://img.shields.io/badge/TensorFlow-2b3137?style=flat-square&logo=tensorflow&logoColor=FF6F00) ![Keras](https://img.shields.io/badge/Keras-2b3137?style=flat-square&logo=keras&logoColor=ffffff) ![scikit-learn](https://img.shields.io/badge/scikit--learn-2b3137?style=flat-square&logo=scikitlearn&logoColor=F7931E) ![XGBoost](https://img.shields.io/badge/XGBoost-2b3137?style=flat-square) |
| **AWS and cloud** | ![Lambda](https://img.shields.io/badge/Lambda-2b3137?style=flat-square) ![S3](https://img.shields.io/badge/S3-2b3137?style=flat-square) ![Redshift](https://img.shields.io/badge/Redshift-2b3137?style=flat-square) ![SageMaker](https://img.shields.io/badge/SageMaker-2b3137?style=flat-square) ![DynamoDB](https://img.shields.io/badge/DynamoDB-2b3137?style=flat-square) ![Glue](https://img.shields.io/badge/Glue-2b3137?style=flat-square) ![CloudWatch](https://img.shields.io/badge/CloudWatch-2b3137?style=flat-square) ![CDK](https://img.shields.io/badge/CDK-2b3137?style=flat-square) ![Terraform](https://img.shields.io/badge/Terraform-2b3137?style=flat-square&logo=terraform&logoColor=844FBA) ![Cloudflare Workers](https://img.shields.io/badge/Cloudflare%20Workers-2b3137?style=flat-square&logo=cloudflare&logoColor=F38020) |
| **Data** | ![PostgreSQL](https://img.shields.io/badge/PostgreSQL-2b3137?style=flat-square&logo=postgresql&logoColor=4169E1) ![MySQL](https://img.shields.io/badge/MySQL-2b3137?style=flat-square&logo=mysql&logoColor=4479A1) ![BigQuery](https://img.shields.io/badge/BigQuery-2b3137?style=flat-square&logo=googlebigquery&logoColor=669DF6) ![DuckDB](https://img.shields.io/badge/DuckDB-2b3137?style=flat-square&logo=duckdb&logoColor=FFF000) ![pandas](https://img.shields.io/badge/pandas-2b3137?style=flat-square&logo=pandas&logoColor=ffffff) ![NumPy](https://img.shields.io/badge/NumPy-2b3137?style=flat-square&logo=numpy&logoColor=ffffff) ![Tableau](https://img.shields.io/badge/Tableau-2b3137?style=flat-square) ![Power BI](https://img.shields.io/badge/Power%20BI-2b3137?style=flat-square) |
| **Tools** | ![Git](https://img.shields.io/badge/Git-2b3137?style=flat-square&logo=git&logoColor=F03C2E) ![GitHub Actions](https://img.shields.io/badge/GitHub%20Actions-2b3137?style=flat-square&logo=githubactions&logoColor=2088FF) ![Docker](https://img.shields.io/badge/Docker-2b3137?style=flat-square&logo=docker&logoColor=2496ED) ![FastAPI](https://img.shields.io/badge/FastAPI-2b3137?style=flat-square&logo=fastapi&logoColor=009688) ![Streamlit](https://img.shields.io/badge/Streamlit-2b3137?style=flat-square&logo=streamlit&logoColor=FF4B4B) ![Jira](https://img.shields.io/badge/Jira-2b3137?style=flat-square&logo=jira&logoColor=0052CC) |

## Certifications

- [AWS Certified Machine Learning Engineer - Associate](https://www.credly.com/badges/ea88a163-447c-49b2-9962-5b959e9258f5), Mar 2026
- [AWS Certified Data Engineer - Associate](https://www.credly.com/badges/4d78e824-4a6f-4dbe-aa84-bbd9d43fe99c), Nov 2024
- [AWS Certified Solutions Architect - Associate](https://www.credly.com/badges/34216190-94e5-4580-a564-934ccaf38586), Jul 2024

## Publication

Teitelbaum, E., Shaik, M.B., & Sharma, S.C. (2026). [The Limits and Promise of Automated Event Coding: Evidence from the South Asia Terrorism Portal](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=6163986). SSRN. LLM and encoder-transformer benchmarking for multi-label political event attribution, with an evaluation methodology.

## Photography

When I'm not building I take photos. They're on Instagram at [@mylenspeak](https://instagram.com/mylenspeak).

<div align="center">

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="https://raw.githubusercontent.com/mohiddin7/mohiddin7/output/github-snake-dark.svg" />
  <source media="(prefers-color-scheme: light)" srcset="https://raw.githubusercontent.com/mohiddin7/mohiddin7/output/github-snake.svg" />
  <img alt="Snake animation eating my contribution graph" src="https://raw.githubusercontent.com/mohiddin7/mohiddin7/output/github-snake.svg" />
</picture>

</div>
