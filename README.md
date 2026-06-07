# GridGuard AI

### Multi-Agent Smart Grid Security Copilot

GridGuard AI is a multi-agent cybersecurity platform designed for smart grid environments. The system extends traditional anomaly detection by combining machine learning, Large Language Models (LLMs), Retrieval-Augmented Generation (RAG), and workflow automation to investigate, explain, and respond to cyber incidents in IEC 61850/MMS-based Industrial Control Systems (ICS).

The project is built as an extension of my Master's Thesis:

**AI-driven Anomaly Detection with ICS Protocols Integration in Smart Grids**

---

# Problem Statement

Traditional anomaly detection systems can identify suspicious activity but often fail to answer critical operational questions:

* Why was this anomaly detected?
* What asset is impacted?
* Is this a cyberattack or operational fault?
* What is the business risk?
* What should operators do next?

GridGuard AI addresses this gap through AI-powered incident investigation and response.

---

# Solution Overview

The platform combines anomaly detection models with a team of specialized LLM agents.

```text
MMS Traffic
     │
     ▼
Anomaly Detection
     │
     ▼
Agent Orchestrator
     │
 ┌───┼─────────────────────┐
 ▼   ▼          ▼         ▼
Detection   Root Cause   Risk   Response
 Agent       Agent      Agent    Agent
     │
     ▼
Incident Report
     │
     ▼
Power Automate
     │
     ▼
Teams / Email Alerts
```

---

# Key Features

## AI-Powered Anomaly Detection

* Isolation Forest
* Local Outlier Factor (LOF)
* Smart Grid Network Monitoring
* MMS Protocol Analysis

---

## Multi-Agent LLM System

### Detection Agent

Analyzes anomaly outputs and identifies suspicious activity.

### Root Cause Agent

Investigates likely causes of anomalous behavior using protocol context and historical events.

### ICS Knowledge Agent

Retrieves information from:

* IEC 61850 documentation
* MMS protocol references
* NIST ICS Security Framework
* MITRE ATT&CK for ICS

### Risk Assessment Agent

Evaluates:

* Asset Criticality
* Operational Impact
* Attack Severity
* Business Risk

### Response Agent

Generates remediation actions and incident response recommendations.

---

# Technology Stack

## AI & Machine Learning

* Python
* Scikit-learn
* Isolation Forest
* Local Outlier Factor

## LLM & Agent Framework

* LangGraph
* LangChain
* Llama 3
* OpenAI GPT
* FAISS

## Smart Grid Technologies

* IEC 61850
* MMS Protocol
* MATLAB Simulink

## Automation & APIs

* FastAPI
* Power Automate
* Microsoft Teams Integration

---

# Repository Structure

```text
agents/
│
├── detection_agent.py
├── rootcause_agent.py
├── risk_agent.py
├── response_agent.py
└── orchestrator.py

detection/
│
├── isolation_forest.py
├── lof_detector.py
└── anomaly_pipeline.py

rag/
│
├── ingest.py
├── vectorstore.py
└── retriever.py

api/
└── app.py
```

---

# Agent Workflow

## Step 1

MMS network traffic is collected from smart grid environments.

## Step 2

Machine learning models identify anomalous patterns.

## Step 3

The orchestrator distributes findings to specialized agents.

## Step 4

Agents investigate anomalies using:

* Detection results
* Historical events
* ICS knowledge base
* Security frameworks

## Step 5

An incident report is generated.

## Step 6

Automated notifications are sent through Power Automate.

---

# Sample Incident Report

```json
{
  "attack_type": "Denial of Service",
  "protocol": "MMS",
  "target": "NAN Gateway",
  "severity": "High",
  "confidence": 0.94,
  "impact": "Communication disruption",
  "recommended_actions": [
    "Throttle MMS Requests",
    "Block Source IP",
    "Enable Enhanced Monitoring"
  ]
}
```

---

# Architecture

![Architecture](screenshots/architecture.png)

---

# Future Enhancements

* Real-time packet ingestion
* SIEM integration
* Microsoft Sentinel integration
* Autonomous remediation workflows
* Digital Twin simulation integration
* Adaptive agent collaboration

---

# Research Background

This project extends research conducted in my Master's Thesis on AI-driven anomaly detection in smart grids using ICS protocols and machine learning techniques.

The objective is to bridge anomaly detection and actionable incident response through explainable AI and multi-agent reasoning.
