* Review the script that checks for available harvest before collection
* Add foreign key validation
* Add global error handling for missing fields and other common errors
* Handle this mess

```
{
  "device": {
    "applicationId": "string",
    "description": "string",
    "devEui": "string",
    "deviceProfileId": "string",
    "isDisabled": true,
    "joinEui": "string",
    "name": "string",
    "skipFcntCheck": true,
    "tags": {
      "additionalProp1": "string",
      "additionalProp2": "string",
      "additionalProp3": "string"
    },
    "variables": {
      "additionalProp1": "string",
      "additionalProp2": "string",
      "additionalProp3": "string"
    }
  }
}
```

Have a function that generates all the euis, sends them to chirpstack, 
then sends the credentials back to the db for storage after the device has 
been created on chirpstack.
The function should also map devices with their sensor capabilities.