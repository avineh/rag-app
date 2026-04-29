import chromadb

# 1. חיבור לאותה תיקייה
client = chromadb.PersistentClient(path="./chroma_data")

# 2. גישה לקולקשן שיצרנו קודם
collection = client.get_collection(name="my_documents")

# 3. נבקש לראות את כל מה שיש בפנים (עד 10 רשומות)
results = collection.get()

print("--- Data in DB ---")
for i in range(len(results['ids'])):
    print(f"ID: {results['ids'][i]}")
    print(f"Text: {results['documents'][i]}")
    print(f"Metadata: {results['metadatas'][i]}")
    print("-" * 20)

# 4. בונוס: כמה רשומות יש סה"כ?
print(f"Total items in collection: {collection.count()}")