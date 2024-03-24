import redis
import json

# Connect to Redis
# Adjust the host, port, and db number according to your Redis configuration
r = redis.Redis(host='localhost', port=6379, db=0)

# Fetch all keys in Redis
keys = r.keys('*')

# Initialize a list to hold your deserialized Redis JSON objects
redis_objects = []

# Iterate over all keys to fetch and deserialize their values
for key in keys:
    # Fetch the value for each key; decoding binary data to string
    value_str = r.get(key).decode('utf-8')

    # Deserialize the JSON string to a Python object
    value_obj = json.loads(value_str)

    # Append the deserialized object to your list
    redis_objects.append(value_obj)

# Serialize and save the list of objects to a JSON file
with open('redis_objects_dump.json', 'w') as json_file:
    json.dump(redis_objects, json_file, indent=4)

print("Redis JSON objects have been dumped into redis_objects_dump.json.")
