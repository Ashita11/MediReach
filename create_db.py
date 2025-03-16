import sqlite3

# Create or connect to a SQLite database (MediReach.sqlite3)
connection = sqlite3.connect('MediReach.sqlite3')

# Create a cursor object to interact with the database
cursor = connection.cursor()

# Example: Create a table for patients in the MediReach database
cursor.execute('''
    CREATE TABLE IF NOT EXISTS patients (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        age INTEGER,
        phone TEXT,
        address TEXT
    )
''')

# Commit the transaction
connection.commit()

# Close the connection
connection.close()

print("MediReach database and patients table created successfully.")
