from sqlalchemy import create_engine, text


connection_string = 'postgresql://ueemr8ld2rv7jl:pbd758327b7bcfbf2eb04abaf31f6ef6fe52f44b274d267927767b0e0ea3b359b@ec2-34-201-142-49.compute-1.amazonaws.com:5432/dcqh91qqh57r0v'
engine = create_engine(connection_string)

try:
    with engine.connect() as connection:
        # Get column names and types
        result = connection.execute(text("SELECT * FROM account_message LIMIT 1"))
        print("Columns:", result.keys())
        
        # Get a sample row to see data format
        row = result.fetchone()
        print("\nSample Row:", row)
        
except Exception as e:
    print(f"Error: {e}")
