import json

try:
    # Try to parse the string as JSON
    data = json.loads('{"skip_sales": false}')
    # Check if it's a dictionary and has the 'skip_sales' key
    if isinstance(data, dict) and "skip_sales" in data:
        print("Sales_Skip: ",data["skip_sales"])
except json.JSONDecodeError:
        print("Decode Err at target html composer")  
         
