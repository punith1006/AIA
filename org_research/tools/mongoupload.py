import os
from pymongo import MongoClient
import requests,json

def create_blank_project(client_id: str):
    from pymongo import MongoClient
    connection_string = os.getenv("MONGO_DB_CONNECTOR")
    client = MongoClient(connection_string)
    db = client["sales_reports"]
    collection = db["org_reports"]

    # Check if a document with the same client_id exists
    existing_doc = collection.find_one({"client_id": client_id})
    
    if existing_doc:
        print(f"Document with client_id '{client_id}' already exists.")
        return True  # No document is created, but returning False would cause pointless tool reruns 

    # If not found, insert the blank document
    document = {
        "client_id": client_id,
        "client_org_research": ""
    }

    collection.insert_one(document)
    print(f"New document created for client_id '{client_id}'.")
    return True 

def update_project_report(client_id: str, report_raw: str, report_html: str, report_type: str):
    """
    Updates the report field (report_type) in the project document with the given client_id.
    """
    mongo_uri = os.getenv("MONGO_DB_CONNECTOR")
    if not mongo_uri:
        raise ValueError("MONGO_DB_CONNECTOR environment variable is not set.")

    client = MongoClient(mongo_uri)
    db = client["sales_reports"]
    collection = db["org_reports"]
    
    # Build update document: set whichever fields are provided
    update_doc = {}
    if report_html is not None:
        update_doc["html_report"] = report_html
    if report_raw is not None:
        update_doc["raw_report"] = report_raw

    result = collection.update_one(
        {"client_id": client_id},
        {"$set": {report_type: update_doc}}
    )
    print(result)
    requests.put(f"https://stu.globalknowledgetech.com:8444/project/project-status-update/{client_id}/",headers = {'Content-Type': 'application/json'}, data = json.dumps({"status": f"{report_type} updated"}))

    client.close()

    if result.matched_count == 0:
        raise ValueError(f"No project found with client_id '{client_id}'")