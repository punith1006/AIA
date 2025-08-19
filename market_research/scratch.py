import requests,json
project_id = "22"
report_type = "Market Context"
r= requests.put(f"https://stu.globalknowledgetech.com:8444/project/project-status-update/{project_id}/",headers = {'Content-Type': 'application/json'}, data = json.dumps({"status": f"{report_type} updated!"}))
print(r.text)