// 1. Tell VS Code to look at the correct database
use('tenet_db'); 

// 2. This query will return the actual data to the results window
db.getCollection('nodes')
  .find({})
  .sort({ _id: -1 }) // Newest message first
  .toArray();       // Important: converts the cursor to a list you can see