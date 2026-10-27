# Northwind HR Policy Assistant

## Project overview

This application allows employees to ask questions about the
Northwind Tech employee handbook through a Streamlit chat interface.

The application connects to a deployed Databricks HR Policy Q&A agent.
The agent retrieves relevant handbook information from the configured
Vector Search index and generates an answer based on the handbook.

## Application files

- `app.py` - Streamlit chatbot interface and agent integration.
- `requirements.txt` - Python dependencies.
- `app.yaml` - Application startup configuration.
- `README.md` - Project documentation.

## Required Databricks resource

Add the deployed model-serving endpoint as an application resource:

`agents_hr_policy-hr_policy_data-hr_policy_qa_agent`

Grant the app the `Can query` permission for this endpoint.

## Deployment

Deploy the application using the Databricks CLI after syncing the
application files to the Databricks workspace.

## Test questions

1. How many annual leave days can I carry over?
2. Do I need a receipt for a $30 expense?
3. How long is parental leave for a secondary caregiver?
4. Can I expense wine at a work dinner?
5. What is the capital of France?
