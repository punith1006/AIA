import os
from pymongo import MongoClient
import requests
import json

def create_blank_project(project_id: str):
    """
    Creates a blank project document in MongoDB with the given project_id.
    The document will have placeholders for specific report fields.
    """
    mongo_uri = os.getenv("MONGO_DB_CONNECTOR")
    if not mongo_uri:
        raise ValueError("MONGO_DB_CONNECTOR environment variable is not set.")

    client = MongoClient(mongo_uri)
    db = client["sales_reports"]
    collection = db["projects"]

    document = {
        "project_id": project_id,
        "client_org_research": None,
        "market_context": None,
        "prospect_research": None,
        "market_segment": None,
        "target_org_research": None
    }

    collection.insert_one(document)
    client.close()


def update_project_report(project_id: str, report: str, report_type: str):
    """
    Updates the report field (report_type) in the project document with the given project_id.
    """
    allowed_fields = {
        "client_org_research",
        "market_context",
        "prospect_research",
        "market_segment",
        "target_org_research"
    }

    if report_type not in allowed_fields:
        raise ValueError(f"Invalid report_type. Must be one of: {', '.join(allowed_fields)}")

    mongo_uri = os.getenv("MONGO_DB_CONNECTOR")
    if not mongo_uri:
        raise ValueError("MONGO_DB_CONNECTOR environment variable is not set.")

    client = MongoClient(mongo_uri)
    db = client["sales_reports"]
    collection = db["projects"]

    result = collection.update_one(
        {"project_id": project_id},
        {"$set": {report_type: report}}
    )

    requests.put(f"https://stu.globalknowledgetech.com:8444/project/project-status-update/{project_id}/",headers = {'Content-Type': 'application/json'}, data = json.dumps({"status": f"{report_type} updated"}))

    client.close()

    if result.matched_count == 0:
        raise ValueError(f"No project found with project_id '{project_id}'")